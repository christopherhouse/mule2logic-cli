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

Correlation IDs (:func:`uuid.uuid4`) and timing (:func:`time.monotonic`)
are managed here and propagated through the context.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from m2la_contracts.enums import InputMode

from m2la_agents.analyzer import AnalyzerAgent
from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus, OrchestrationResult, StepResult
from m2la_agents.planner import PlannerAgent
from m2la_agents.repair_advisor import RepairAdvisorAgent
from m2la_agents.transformer import TransformerAgent
from m2la_agents.validator import ValidatorAgent


class MigrationOrchestrator:
    """Runs the full migration pipeline through a sequence of agents.

    Usage::

        orchestrator = MigrationOrchestrator()
        result = orchestrator.run(
            input_path="/path/to/mule-project",
        )
        print(result.overall_status)
        for step in result.steps:
            print(step.step_name, step.agent_result.reasoning_summary)

    Attributes:
        agents: Ordered list of agents in the pipeline.
        include_repair: Whether to include the repair advisor step.
    """

    def __init__(
        self,
        *,
        agents: list[BaseAgent] | None = None,
        include_repair: bool = True,
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

        Creates a fresh :class:`AgentContext` with a correlation ID and
        runs each agent in sequence. Stops on the first ``FAILURE`` status.

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
