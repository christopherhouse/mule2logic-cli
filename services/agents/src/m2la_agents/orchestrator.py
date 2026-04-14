"""MigrationOrchestrator — runs the full agent pipeline.

Pipeline stages:

1. **Analyze**   — parse input, build IR, validate input
2. **Plan**      — evaluate mapping availability, produce migration plan
3. **Transform** — generate Logic Apps artifacts
4. **Validate**  — validate generated output
5. **Repair**    — (optional) suggest fixes for issues and gaps

All migration requests flow through the LLM-backed agent orchestrator.
The orchestrator uses ``SequentialBuilder`` from
``agent_framework.orchestrations`` to chain agents into a sequential
workflow.  Each agent is a MAF ``Agent`` with registered tool functions
and domain-specific instructions.  The LLM reasons about each pipeline
stage, invokes deterministic tool functions, and produces structured
results.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from m2la_contracts.enums import InputMode
from opentelemetry import metrics, trace

from m2la_agents.analyzer import AnalyzerAgent
from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentResult, AgentStatus, OrchestrationResult, StepResult
from m2la_agents.planner import PlannerAgent
from m2la_agents.repair_advisor import RepairAdvisorAgent
from m2la_agents.token_estimator import estimate_message_tokens, estimate_text_tokens
from m2la_agents.transformer import TransformerAgent
from m2la_agents.validator import ValidatorAgent

if TYPE_CHECKING:
    from agent_framework import Agent

logger = logging.getLogger(__name__)

_tracer = trace.get_tracer("m2la.agents")
_meter = metrics.get_meter("m2la.agents")

# Agent metrics
_agent_invocations = _meter.create_counter("m2la.agent.invocations", description="Per-agent invocation count", unit="1")
_agent_duration = _meter.create_histogram(
    "m2la.agent.duration_ms", description="Per-agent execution duration in ms", unit="ms"
)
_agent_errors = _meter.create_counter("m2la.agent.errors", description="Agent error count", unit="1")

# Pipeline metrics
_pipeline_requests = _meter.create_counter("m2la.pipeline.requests", description="Total pipeline invocations", unit="1")
_pipeline_duration = _meter.create_histogram(
    "m2la.pipeline.duration_ms", description="Pipeline duration in ms", unit="ms"
)
_pipeline_active = _meter.create_up_down_counter("m2la.pipeline.active", description="In-flight pipelines", unit="1")

# LLM / Token metrics
_llm_estimated_prompt = _meter.create_counter(
    "m2la.llm.estimated_prompt_tokens", description="Estimated prompt tokens via tiktoken", unit="token"
)
_llm_estimated_completion = _meter.create_counter(
    "m2la.llm.estimated_completion_tokens", description="Estimated completion tokens via tiktoken", unit="token"
)
_llm_actual_prompt = _meter.create_counter(
    "m2la.llm.actual_prompt_tokens", description="Actual prompt tokens from LLM API", unit="token"
)
_llm_actual_completion = _meter.create_counter(
    "m2la.llm.actual_completion_tokens", description="Actual completion tokens from LLM API", unit="token"
)
_llm_actual_total = _meter.create_counter(
    "m2la.llm.actual_total_tokens", description="Actual total tokens from LLM API", unit="token"
)
_llm_calls = _meter.create_counter("m2la.llm.calls", description="Total LLM API calls", unit="1")
_llm_latency = _meter.create_histogram("m2la.llm.latency_ms", description="LLM call latency in ms", unit="ms")

_MAX_REASONING_SUMMARY_LEN = 200


class MigrationOrchestrator:
    """Runs the full migration pipeline through a sequence of LLM-backed agents.

    Every migration request flows through the LLM via a
    ``SequentialBuilder`` workflow.  The ``client`` parameter (a
    ``FoundryChatClient`` or compatible) is **required**.

    Usage::

        from agent_framework.foundry import FoundryChatClient
        from azure.identity import AzureCliCredential

        client = FoundryChatClient(
            project_endpoint="https://...",
            model="gpt-4o",
            credential=AzureCliCredential(),
        )
        orchestrator = MigrationOrchestrator(client=client)
        result = orchestrator.run(input_path="/path/to/mule-project")
    """

    def __init__(
        self,
        *,
        agents: list[BaseAgent] | None = None,
        include_repair: bool = True,
        client: Any,
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
        """Execute the full migration pipeline through the LLM.

        Always flows through the ``SequentialBuilder`` → LLM → tool
        calls path.  There is no offline bypass.
        """
        cid = correlation_id or str(uuid.uuid4())
        pipeline_start = time.monotonic()
        _pipeline_active.add(1)

        with _tracer.start_as_current_span("m2la.orchestrate") as span:
            span.set_attribute("correlation_id", cid)
            span.set_attribute("input.path", input_path)
            if input_mode:
                span.set_attribute("input.mode", input_mode.value)

            # Handle empty agent list early
            if not self.agents:
                total_ms = (time.monotonic() - pipeline_start) * 1000
                _pipeline_active.add(-1)
                _pipeline_requests.add(1, {"status": "success"})
                _pipeline_duration.record(total_ms)
                return OrchestrationResult(
                    correlation_id=cid,
                    steps=[],
                    overall_status=AgentStatus.SUCCESS,
                    total_duration_ms=total_ms,
                    final_output=None,
                )

            # Build MAF agents from our BaseAgent wrappers
            maf_agents: list[Agent] = []
            for agent in self.agents:
                maf_agent = agent.build_maf_agent(self.client)
                maf_agents.append(maf_agent)
                logger.info("Built MAF agent: %s", agent.name)

            # Build SequentialBuilder workflow
            from agent_framework.orchestrations import SequentialBuilder

            workflow = SequentialBuilder(participants=maf_agents).build()

            # Construct user message describing the migration task
            mode_str = input_mode.value if input_mode else "auto-detect"
            user_message = (
                f"Migrate the MuleSoft project at: {input_path}\n"
                f"Input mode: {mode_str}\n"
                f"Output directory: {output_directory or 'default'}\n"
                f"Correlation ID: {cid}"
            )

            # Estimate prompt tokens for each agent's system prompt + user message
            for agent in self.agents:
                messages = [
                    {"role": "system", "content": agent.instructions},
                    {"role": "user", "content": user_message},
                ]
                est_prompt = estimate_message_tokens(messages)
                _llm_estimated_prompt.add(est_prompt, {"agent_name": agent.name})

            # Execute the workflow
            step_results: list[StepResult] = []
            try:
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    pass  # No running loop — safe to use asyncio.run()
                else:
                    msg = (
                        "MigrationOrchestrator.run() cannot execute from a running event loop. "
                        "Use an async orchestration entry point instead."
                    )
                    logger.error(msg)
                    raise RuntimeError(msg)

                llm_start = time.monotonic()
                step_results = asyncio.run(
                    self._execute_workflow(workflow, user_message),
                )
                llm_elapsed = (time.monotonic() - llm_start) * 1000
                _llm_calls.add(1, {"status": "success"})
                _llm_latency.record(llm_elapsed)
                logger.info("Workflow completed with %d step(s)", len(step_results))
            except RuntimeError:
                raise  # Propagate loop-detection error
            except Exception:
                _llm_calls.add(1, {"status": "error"})
                logger.exception("Workflow execution failed")

            # Emit per-agent metrics from step results
            for step in step_results:
                attrs = {"agent_name": step.step_name, "status": step.agent_result.status.value}
                _agent_invocations.add(1, attrs)
                _agent_duration.record(step.agent_result.duration_ms, {"agent_name": step.step_name})
                if step.agent_result.status == AgentStatus.FAILURE:
                    _agent_errors.add(1, {"agent_name": step.step_name})

                # Estimate completion tokens from response text
                reasoning = step.agent_result.reasoning_summary or ""
                est_completion = estimate_text_tokens(reasoning)
                _llm_estimated_completion.add(est_completion, {"agent_name": step.step_name})

            # Derive overall status from step results
            overall_status = AgentStatus.SUCCESS
            final_output: Any = None

            for step in step_results:
                if step.agent_result.status == AgentStatus.FAILURE:
                    overall_status = AgentStatus.FAILURE
                    break
                if step.agent_result.status == AgentStatus.PARTIAL:
                    overall_status = AgentStatus.PARTIAL
                final_output = step.agent_result.output

            total_ms = (time.monotonic() - pipeline_start) * 1000
            span.set_attribute("pipeline.status", overall_status.value)
            span.set_attribute("pipeline.steps", len(step_results))
            span.set_attribute("pipeline.duration_ms", total_ms)

            _pipeline_active.add(-1)
            _pipeline_requests.add(1, {"status": overall_status.value})
            _pipeline_duration.record(total_ms)

            return OrchestrationResult(
                correlation_id=cid,
                steps=step_results,
                overall_status=overall_status,
                total_duration_ms=total_ms,
                final_output=final_output,
            )

    # ------------------------------------------------------------------
    # Workflow execution
    # ------------------------------------------------------------------

    async def _execute_workflow(
        self,
        workflow: Any,
        user_message: str,
    ) -> list[StepResult]:
        """Run the SequentialBuilder workflow and extract step results.

        Each agent in the sequential workflow calls a tool function and
        returns the result as assistant text.  The final ``output`` event
        contains the full conversation with one assistant message per
        agent.  We parse those messages into :class:`StepResult` entries.

        Also captures actual token usage from MAF events when available.
        """
        final_conversation: list[Any] = []

        async for event in workflow.run(user_message, stream=True):
            if event.type == "output":
                final_conversation = event.data if event.data else []

            # Capture actual token usage if exposed by the event
            usage = getattr(event, "usage", None) or (
                event.data.get("usage") if isinstance(getattr(event, "data", None), dict) else None
            )
            if usage and isinstance(usage, dict):
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                if prompt_tokens:
                    _llm_actual_prompt.add(prompt_tokens)
                if completion_tokens:
                    _llm_actual_completion.add(completion_tokens)
                if total_tokens:
                    _llm_actual_total.add(total_tokens)

        return self._parse_conversation_steps(final_conversation)

    def _parse_conversation_steps(
        self,
        conversation: list[Any],
    ) -> list[StepResult]:
        """Parse the final conversation into StepResult entries.

        Each assistant message in the conversation corresponds to one
        agent's tool output.  We match them to our ``self.agents`` list
        by position.
        """
        now = datetime.now(UTC)
        steps: list[StepResult] = []
        agent_idx = 0

        for msg in conversation:
            role = getattr(msg, "role", "")
            if role != "assistant":
                continue

            text = getattr(msg, "text", "") or ""
            agent_name = self.agents[agent_idx].name if agent_idx < len(self.agents) else f"Agent-{agent_idx}"
            agent_idx += 1

            # Try to parse the tool output as JSON
            output: Any = None
            status = AgentStatus.SUCCESS
            error_message: str | None = None

            try:
                parsed = json.loads(text)
                output = parsed

                # Check for failure indicators in the tool output
                if isinstance(parsed, dict):
                    if "error" in parsed:
                        status = AgentStatus.FAILURE
                        error_message = str(parsed["error"])
                    elif parsed.get("valid") is False:
                        status = AgentStatus.PARTIAL
            except (json.JSONDecodeError, TypeError):
                output = text if text else None

            agent_result = AgentResult(
                agent_name=agent_name,
                status=status,
                output=output,
                reasoning_summary=text[:_MAX_REASONING_SUMMARY_LEN] if text else f"{agent_name} completed",
                error_message=error_message,
            )
            steps.append(
                StepResult(
                    step_name=agent_name,
                    agent_result=agent_result,
                    started_at=now,
                    completed_at=now,
                )
            )

            # Stop pipeline on failure
            if status == AgentStatus.FAILURE:
                break

        return steps
