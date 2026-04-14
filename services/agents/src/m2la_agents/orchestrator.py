"""MigrationOrchestrator — runs the full agent pipeline.

Pipeline stages:

1. **Analyze**   — parse input, build IR, validate input
2. **Plan**      — evaluate mapping availability, produce migration plan
3. **Transform** — generate Logic Apps artifacts
4. **Validate**  — validate generated output
5. **Repair**    — (optional) suggest fixes for issues and gaps

**Online mode** (Microsoft Agent Framework):

Uses ``SequentialBuilder`` from ``agent_framework.orchestrations`` to chain
agents into a sequential workflow.  Each agent is a MAF ``Agent`` with
registered tool functions and domain-specific instructions.  The LLM reasons
about the migration pipeline, invokes tool functions, and produces a coherent
migration summary.

**Offline mode** (default):

Each step's output is deposited into the shared :class:`AgentContext`.
If any step returns ``FAILURE``, the pipeline stops.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from m2la_contracts.enums import InputMode

from m2la_agents.analyzer import AnalyzerAgent
from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus, OrchestrationResult, StepResult
from m2la_agents.planner import PlannerAgent
from m2la_agents.repair_advisor import RepairAdvisorAgent
from m2la_agents.sdk_config import FoundryClientConfig
from m2la_agents.transformer import TransformerAgent
from m2la_agents.validator import ValidatorAgent

if TYPE_CHECKING:
    from agent_framework import Agent

logger = logging.getLogger(__name__)


class MigrationOrchestrator:
    """Runs the full migration pipeline through a sequence of agents.

    Supports two execution modes:

    * **Offline** (default) — each agent's :meth:`~BaseAgent.execute`
      method is called directly.  No LLM calls or network access.
    * **Online** — agents are constructed as MAF ``Agent`` instances
      with a ``FoundryChatClient``, then composed into a
      ``SequentialBuilder`` workflow for multi-agent orchestration.

    Usage::

        # Offline (tests / CI)
        orchestrator = MigrationOrchestrator()
        result = orchestrator.run(input_path="/path/to/mule-project")

        # Online (with Azure AI Foundry)
        from agent_framework.foundry import FoundryChatClient
        from azure.identity import AzureCliCredential

        client = FoundryChatClient(
            project_endpoint="https://...",
            model="gpt-4o",
            credential=AzureCliCredential(),
        )
        config = FoundryClientConfig(endpoint="https://...", model="gpt-4o")
        orchestrator = MigrationOrchestrator(client=client, config=config)
        result = orchestrator.run(input_path="/path/to/mule-project")
    """

    def __init__(
        self,
        *,
        agents: list[BaseAgent] | None = None,
        include_repair: bool = True,
        client: Any | None = None,
        config: FoundryClientConfig | None = None,
    ) -> None:
        if agents is not None:
            self.agents = agents
        else:
            base: list[BaseAgent] = [
                AnalyzerAgent(),
                PlannerAgent(),
                TransformerAgent(),
                ValidatorAgent(),
            ]
            if include_repair:
                base.append(RepairAdvisorAgent())
            self.agents = base
        self.include_repair = include_repair
        self.client = client
        self.config = config or FoundryClientConfig()

    def run(
        self,
        input_path: str,
        *,
        input_mode: InputMode | None = None,
        output_directory: str | None = None,
        correlation_id: str | None = None,
        trace_id: str = "",
        span_id: str = "",
        metadata: dict | None = None,
    ) -> OrchestrationResult:
        """Execute the full migration pipeline.

        Selects online or offline mode based on whether a chat client
        was provided.
        """
        if self.client is not None:
            return self._run_online(
                input_path,
                input_mode=input_mode,
                output_directory=output_directory,
                correlation_id=correlation_id,
                trace_id=trace_id,
                span_id=span_id,
                metadata=metadata,
            )
        return self._run_offline(
            input_path,
            input_mode=input_mode,
            output_directory=output_directory,
            correlation_id=correlation_id,
            trace_id=trace_id,
            span_id=span_id,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Online mode — Microsoft Agent Framework SequentialBuilder
    # ------------------------------------------------------------------

    def _run_online(
        self,
        input_path: str,
        *,
        input_mode: InputMode | None = None,
        output_directory: str | None = None,
        correlation_id: str | None = None,
        trace_id: str = "",
        span_id: str = "",
        metadata: dict | None = None,
    ) -> OrchestrationResult:
        """Run using the Microsoft Agent Framework with SequentialBuilder.

        1. Build MAF ``Agent`` instances from each sub-agent.
        2. Compose them into a ``SequentialBuilder`` workflow.
        3. Run the workflow with a user message describing the task.
        4. Also run the deterministic offline path for structured results.
        """
        cid = correlation_id or str(uuid.uuid4())
        pipeline_start = time.monotonic()

        context = AgentContext(
            correlation_id=cid,
            trace_id=trace_id,
            span_id=span_id,
            input_mode=input_mode,
            input_path=input_path,
            output_directory=output_directory,
            metadata=metadata or {},
        )

        # Step 1: Build MAF agents from our BaseAgent wrappers
        maf_agents: list[Agent] = []
        for agent in self.agents:
            maf_agent = agent.build_maf_agent(self.client)
            maf_agents.append(maf_agent)
            logger.info("Built MAF agent: %s", agent.name)

        # Step 2: Build SequentialBuilder workflow
        from agent_framework.orchestrations import SequentialBuilder

        workflow = SequentialBuilder(participants=maf_agents).build()

        # Step 3: Run the workflow with a migration request message
        mode_str = input_mode.value if input_mode else "auto-detect"
        user_message = (
            f"Migrate the MuleSoft project at: {input_path}\n"
            f"Input mode: {mode_str}\n"
            f"Output directory: {output_directory or 'default'}\n"
            f"Correlation ID: {cid}"
        )

        orchestrator_response = ""
        try:
            orchestrator_response = asyncio.run(self._execute_workflow(workflow, user_message))
            logger.info("Workflow completed with response length: %d", len(orchestrator_response))
        except Exception:
            logger.warning("Online workflow execution failed, using offline results only", exc_info=True)

        # Step 4: Run deterministic path for structured AgentResult objects
        steps: list[StepResult] = []
        overall_status = AgentStatus.SUCCESS
        final_output = None

        for agent in self.agents:
            step_start = datetime.now(UTC)
            result: AgentResult = agent.execute(context)
            step_end = datetime.now(UTC)

            step = StepResult(
                step_name=agent.name,
                agent_result=result,
                started_at=step_start,
                completed_at=step_end,
            )
            steps.append(step)

            if result.status == AgentStatus.FAILURE:
                overall_status = AgentStatus.FAILURE
                break
            if result.status == AgentStatus.PARTIAL:
                overall_status = AgentStatus.PARTIAL
            final_output = result.output

        # Attach the LLM's reasoning
        if orchestrator_response and isinstance(final_output, dict):
            final_output["orchestrator_reasoning"] = orchestrator_response

        total_ms = (time.monotonic() - pipeline_start) * 1000

        return OrchestrationResult(
            correlation_id=cid,
            steps=steps,
            overall_status=overall_status,
            total_duration_ms=total_ms,
            final_output=final_output,
        )

    @staticmethod
    async def _execute_workflow(workflow: Any, user_message: str) -> str:
        """Run the SequentialBuilder workflow and extract the final response."""
        outputs: list[list[Any]] = []
        async for event in workflow.run(user_message, stream=True):
            if event.type == "output":
                outputs.append(event.data)

        if outputs:
            last_conversation = outputs[-1]
            # Get the last assistant message
            for msg in reversed(last_conversation):
                if msg.role == "assistant" and msg.text:
                    return msg.text
        return ""

    # ------------------------------------------------------------------
    # Offline mode — deterministic logic only
    # ------------------------------------------------------------------

    def _run_offline(
        self,
        input_path: str,
        *,
        input_mode: InputMode | None = None,
        output_directory: str | None = None,
        correlation_id: str | None = None,
        trace_id: str = "",
        span_id: str = "",
        metadata: dict | None = None,
    ) -> OrchestrationResult:
        """Run in offline mode — deterministic logic only."""
        cid = correlation_id or str(uuid.uuid4())
        pipeline_start = time.monotonic()

        context = AgentContext(
            correlation_id=cid,
            trace_id=trace_id,
            span_id=span_id,
            input_mode=input_mode,
            input_path=input_path,
            output_directory=output_directory,
            metadata=metadata or {},
        )

        steps: list[StepResult] = []
        overall_status = AgentStatus.SUCCESS
        final_output = None

        for agent in self.agents:
            step_start = datetime.now(UTC)
            result: AgentResult = agent.execute(context)
            step_end = datetime.now(UTC)

            step = StepResult(
                step_name=agent.name,
                agent_result=result,
                started_at=step_start,
                completed_at=step_end,
            )
            steps.append(step)

            if result.status == AgentStatus.FAILURE:
                overall_status = AgentStatus.FAILURE
                break

            if result.status == AgentStatus.PARTIAL:
                overall_status = AgentStatus.PARTIAL

            final_output = result.output

        total_ms = (time.monotonic() - pipeline_start) * 1000

        return OrchestrationResult(
            correlation_id=cid,
            steps=steps,
            overall_status=overall_status,
            total_duration_ms=total_ms,
            final_output=final_output,
        )
