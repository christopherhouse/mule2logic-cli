"""MigrationOrchestrator — runs the full agent pipeline.

Pipeline stages:

1. **Analyze**   — parse input, build IR, validate input
2. **Plan**      — evaluate mapping availability, produce migration plan
3. **Transform** — generate Logic Apps artifacts
4. **Validate**  — validate generated output
5. **Repair**    — (optional) suggest fixes for issues and gaps

Each step's output is deposited into the shared :class:`AgentContext` and
feeds into the next step. If any step returns ``FAILURE``, the pipeline
stops and returns a partial :class:`OrchestrationResult`.

When an ``AgentsClient`` is provided the orchestrator creates agents on the
Azure AI Agent Service and uses LLM-backed runs.  When no client is
provided (the default) the pipeline runs in **offline mode** — each agent's
:meth:`~BaseAgent.execute` is called directly.

Correlation IDs (:func:`uuid.uuid4`) and timing (:func:`time.monotonic`)
are managed here and propagated through the context.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from m2la_contracts.enums import InputMode

from m2la_agents.analyzer import AnalyzerAgent
from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus, OrchestrationResult, StepResult
from m2la_agents.planner import PlannerAgent
from m2la_agents.repair_advisor import RepairAdvisorAgent
from m2la_agents.sdk_config import AgentsClientConfig
from m2la_agents.transformer import TransformerAgent
from m2la_agents.validator import ValidatorAgent

if TYPE_CHECKING:
    from azure.ai.agents import AgentsClient

logger = logging.getLogger(__name__)


class MigrationOrchestrator:
    """Runs the full migration pipeline through a sequence of agents.

    Supports two execution modes:

    * **Offline** (default) — each agent's :meth:`~BaseAgent.execute`
      method is called directly.  No LLM calls or network access.
    * **Online** — agents are created on the Azure AI Agent Service via
      ``AgentsClient`` and runs use LLM-backed reasoning with the
      registered :class:`FunctionTool` callables.

    Usage::

        # Offline (tests / CI)
        orchestrator = MigrationOrchestrator()
        result = orchestrator.run(input_path="/path/to/mule-project")

        # Online (with Azure AI Agent Service)
        from azure.ai.agents import AgentsClient
        from azure.identity import DefaultAzureCredential

        client = AgentsClient(
            endpoint="https://...",
            credential=DefaultAzureCredential(),
        )
        orchestrator = MigrationOrchestrator(client=client)
        result = orchestrator.run(input_path="/path/to/mule-project")

    Attributes:
        agents: Ordered list of agents in the pipeline.
        include_repair: Whether to include the repair advisor step.
        client: Optional ``AgentsClient`` for online mode.
        config: SDK configuration (model deployment, endpoint, etc.).
    """

    def __init__(
        self,
        *,
        agents: list[BaseAgent] | None = None,
        include_repair: bool = True,
        client: AgentsClient | None = None,
        config: AgentsClientConfig | None = None,
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
        self.config = config or AgentsClientConfig()

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

        Automatically selects **online** or **offline** mode based on
        whether an ``AgentsClient`` was provided at construction time.

        Args:
            input_path: Path to MuleSoft project or flow XML.
            input_mode: Optional input mode override.
            output_directory: Optional output directory for generated artifacts.
            correlation_id: Optional correlation ID (generated if not provided).
            trace_id: OpenTelemetry trace ID for observability.
            span_id: OpenTelemetry span ID for observability.
            metadata: Additional metadata to attach to the context.

        Returns:
            An :class:`OrchestrationResult` with all step results.
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
    # Online mode — Azure AI Agent Service
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
        """Run using Azure AI Agents Service.

        Creates agents on the service, enables auto function calls,
        creates threads and runs for each agent in sequence, collects
        results, then cleans up.
        """
        assert self.client is not None  # ensured by caller

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

        try:
            # Register agents on the service
            for agent in self.agents:
                agent.create_on_service(self.client, self.config.model_deployment)
                self.client.enable_auto_function_calls(agent.toolset)

            # Run each agent in sequence via thread + run
            for agent in self.agents:
                step_start = datetime.now(UTC)

                try:
                    thread = self.client.threads.create()
                    self.client.messages.create(
                        thread_id=thread.id,
                        role="user",
                        content=(f"Process the migration step for input: {input_path}. Correlation ID: {cid}."),
                    )

                    run = self.client.runs.create_and_process(
                        thread_id=thread.id,
                        agent_id=agent.sdk_agent_id,
                    )
                    logger.info(
                        "Agent %s run completed: status=%s, id=%s",
                        agent.name,
                        run.status,
                        run.id,
                    )

                    # The function tools ran deterministically; fall back
                    # to the offline result for structured output.
                    result: AgentResult = agent.execute(context)

                except Exception as exc:
                    logger.warning("Online run failed for %s, falling back to offline: %s", agent.name, exc)
                    result = agent.execute(context)

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

        finally:
            # Always clean up agents from the service
            for agent in self.agents:
                try:
                    agent.cleanup(self.client)
                except Exception:
                    logger.warning("Failed to clean up agent %s", agent.name, exc_info=True)

        total_ms = (time.monotonic() - pipeline_start) * 1000

        return OrchestrationResult(
            correlation_id=cid,
            steps=steps,
            overall_status=overall_status,
            total_duration_ms=total_ms,
            final_output=final_output,
        )

    # ------------------------------------------------------------------
    # Offline mode — deterministic logic only (existing behaviour)
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
        """Run in offline mode — deterministic logic only.

        This is the original execution path used in tests and CI.
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
