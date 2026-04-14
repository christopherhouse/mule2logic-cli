"""MigrationOrchestrator — runs the full agent pipeline.

Pipeline stages:

1. **Analyze**   — parse input, build IR, validate input
2. **Plan**      — evaluate mapping availability, produce migration plan
3. **Transform** — generate Logic Apps artifacts
4. **Validate**  — validate generated output
5. **Repair**    — (optional) suggest fixes for issues and gaps

**Online mode** (Azure AI Agent Service):

The orchestrator creates each sub-agent on the service, then creates a
**main orchestrator agent** that references the sub-agents as
:class:`~azure.ai.agents.models.ConnectedAgentTool` definitions.
A single thread + run is created for the main agent, which uses LLM
reasoning to delegate tasks to sub-agents and collect their results.

**Offline mode** (default):

Each step's output is deposited into the shared :class:`AgentContext` and
feeds into the next step. If any step returns ``FAILURE``, the pipeline
stops and returns a partial :class:`OrchestrationResult`.

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
from m2la_agents.prompts import ORCHESTRATOR_PROMPT
from m2la_agents.repair_advisor import RepairAdvisorAgent
from m2la_agents.sdk_config import AgentsClientConfig
from m2la_agents.transformer import TransformerAgent
from m2la_agents.validator import ValidatorAgent

if TYPE_CHECKING:
    from azure.ai.agents import AgentsClient

logger = logging.getLogger(__name__)

# Descriptions used by the orchestrator LLM to decide when to delegate.
_AGENT_DESCRIPTIONS: dict[str, str] = {
    "AnalyzerAgent": (
        "Parses and analyzes MuleSoft input (project or single flow XML). "
        "Invoke to discover flows, sub-flows, constructs, and input issues."
    ),
    "PlannerAgent": (
        "Evaluates mapping availability for each MuleSoft construct and "
        "produces a migration plan with supported/unsupported/partial counts."
    ),
    "TransformerAgent": (
        "Converts the MuleSoft IR into Logic Apps Standard artifacts "
        "(workflow.json, host.json, connections.json). Reports migration gaps."
    ),
    "ValidatorAgent": (
        "Validates generated Logic Apps artifacts for schema correctness "
        "and completeness. Reports validation issues with rule IDs."
    ),
    "RepairAdvisorAgent": (
        "Analyzes validation failures and migration gaps, then suggests "
        "actionable repair strategies with confidence levels."
    ),
}


class MigrationOrchestrator:
    """Runs the full migration pipeline through a sequence of agents.

    Supports two execution modes:

    * **Offline** (default) — each agent's :meth:`~BaseAgent.execute`
      method is called directly.  No LLM calls or network access.
    * **Online** — a multi-agent setup is created on the Azure AI Agent
      Service.  Sub-agents are registered as
      :class:`~azure.ai.agents.models.ConnectedAgentTool` definitions
      on a main orchestrator agent.  The orchestrator LLM delegates
      tasks to sub-agents via threads + runs, each sub-agent invokes
      its ``FunctionTool`` callables deterministically.

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
        config = AgentsClientConfig(
            endpoint="https://...",
            model_deployment="gpt-4o",
        )
        orchestrator = MigrationOrchestrator(client=client, config=config)
        result = orchestrator.run(input_path="/path/to/mule-project")

    Attributes:
        agents: Ordered list of sub-agents in the pipeline.
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
    # Online mode — multi-agent via ConnectedAgentTool
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
        """Run using the Azure AI Agent Service with multi-agent orchestration.

        1. Create each sub-agent on the service with its ``FunctionTool``.
        2. Enable auto-function-calls so the SDK invokes tools automatically.
        3. Wire sub-agents as ``ConnectedAgentTool`` on the main orchestrator.
        4. Create a thread, post the user's migration request as a message.
        5. Run the orchestrator agent — it delegates to sub-agents via the
           LLM's natural-language routing.
        6. Extract the agent's response from the thread messages.
        7. Also run the deterministic offline path to collect structured data.
        8. Clean up all agents from the service.
        """
        assert self.client is not None  # ensured by caller

        cid = correlation_id or str(uuid.uuid4())
        pipeline_start = time.monotonic()
        model = self.config.model_deployment

        context = AgentContext(
            correlation_id=cid,
            trace_id=trace_id,
            span_id=span_id,
            input_mode=input_mode,
            input_path=input_path,
            output_directory=output_directory,
            metadata=metadata or {},
        )

        orchestrator_agent_id: str | None = None

        try:
            # ---- Step 1: Create sub-agents on the service ----------------
            for agent in self.agents:
                agent.create_on_service(self.client, model)
                self.client.enable_auto_function_calls(agent.toolset)
                logger.info(
                    "Created sub-agent %s on service (id=%s)",
                    agent.name,
                    agent.sdk_agent_id,
                )

            # ---- Step 2: Wire sub-agents as ConnectedAgentTool -----------
            connected_tools: list = []
            for agent in self.agents:
                description = _AGENT_DESCRIPTIONS.get(
                    agent.name,
                    f"Sub-agent: {agent.name}",
                )
                connected = agent.as_connected_agent_tool(description)
                connected_tools.extend(connected.definitions)

            # ---- Step 3: Create the main orchestrator agent --------------
            orchestrator_agent = self.client.create_agent(
                model=model,
                name="MigrationOrchestrator",
                instructions=ORCHESTRATOR_PROMPT,
                tools=connected_tools,
            )
            orchestrator_agent_id = orchestrator_agent.id
            logger.info(
                "Created orchestrator agent (id=%s) with %d connected sub-agents",
                orchestrator_agent_id,
                len(self.agents),
            )

            # ---- Step 4: Create a thread and post the migration request --
            thread = self.client.threads.create()
            logger.info("Created thread (id=%s)", thread.id)

            # Build a rich user message with all the context
            mode_str = input_mode.value if input_mode else "auto-detect"
            user_message = (
                f"Please migrate the MuleSoft project at: {input_path}\n\n"
                f"Configuration:\n"
                f"- Input mode: {mode_str}\n"
                f"- Output directory: {output_directory or 'default'}\n"
                f"- Correlation ID: {cid}\n\n"
                f"Execute the full migration pipeline: "
                f"analyze → plan → transform → validate → repair.\n"
                f"Report the results from each step."
            )

            from azure.ai.agents.models import MessageRole

            self.client.messages.create(
                thread_id=thread.id,
                role=MessageRole.USER,
                content=user_message,
            )

            # ---- Step 5: Run the orchestrator agent ----------------------
            run = self.client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=orchestrator_agent_id,
            )
            logger.info(
                "Orchestrator run completed: status=%s, id=%s",
                run.status,
                run.id,
            )

            # ---- Step 6: Extract the agent's response --------------------
            agent_response = ""
            if hasattr(run, "status") and run.status == "failed":
                error_msg = getattr(run, "last_error", None)
                logger.warning("Orchestrator run failed: %s", error_msg)
            else:
                messages = self.client.messages.list(thread_id=thread.id)
                for msg in messages:
                    if hasattr(msg, "role") and str(msg.role) == "MessageRole.AGENT":
                        if hasattr(msg, "text_messages") and msg.text_messages:
                            agent_response = msg.text_messages[-1].text.value
                            break

            # ---- Step 7: Run deterministic path for structured output ----
            # The online path gives us LLM reasoning; the offline path
            # gives us the structured AgentResult objects we need.
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

            # Attach the LLM's reasoning to the final output
            if agent_response:
                if final_output is None:
                    final_output = {}
                if isinstance(final_output, dict):
                    final_output["orchestrator_reasoning"] = agent_response

        finally:
            # ---- Step 8: Clean up all agents from the service ------------
            if orchestrator_agent_id:
                try:
                    self.client.delete_agent(orchestrator_agent_id)
                    logger.info("Deleted orchestrator agent %s", orchestrator_agent_id)
                except Exception:
                    logger.warning(
                        "Failed to delete orchestrator agent %s",
                        orchestrator_agent_id,
                        exc_info=True,
                    )

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
