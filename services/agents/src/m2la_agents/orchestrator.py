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

from m2la_agents.analyzer import AnalyzerAgent
from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus, OrchestrationResult, StepResult
from m2la_agents.planner import PlannerAgent
from m2la_agents.repair_advisor import RepairAdvisorAgent
from m2la_agents.transformer import TransformerAgent
from m2la_agents.validator import ValidatorAgent

if TYPE_CHECKING:
    from agent_framework import Agent

logger = logging.getLogger(__name__)


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

        # Handle empty agent list early
        if not self.agents:
            total_ms = (time.monotonic() - pipeline_start) * 1000
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

            step_results = asyncio.run(
                self._execute_workflow(workflow, user_message),
            )
            logger.info("Workflow completed with %d step(s)", len(step_results))
        except RuntimeError:
            raise  # Propagate loop-detection error
        except Exception:
            logger.exception("Workflow execution failed")

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

        Captures ``executor_invoked`` / ``executor_completed`` events to
        build :class:`StepResult` entries from tool call outputs that
        flow through the LLM conversation.  Falls back to parsing the
        final ``output`` event when executor events are unavailable.
        """
        steps: list[StepResult] = []
        current_step_start: datetime | None = None
        current_agent_name: str | None = None
        final_conversation: list[Any] = []

        async for event in workflow.run(user_message, stream=True):
            if event.type == "executor_invoked":
                current_step_start = datetime.now(UTC)
                # The agent name is in the event data or can be inferred
                if hasattr(event, "participant") and event.participant:
                    current_agent_name = getattr(event.participant, "name", None)

            elif event.type == "executor_completed":
                step_end = datetime.now(UTC)
                start = current_step_start or step_end

                # Extract the agent response from the event
                agent_result = self._extract_agent_result(
                    event,
                    current_agent_name,
                )

                if agent_result:
                    steps.append(
                        StepResult(
                            step_name=agent_result.agent_name,
                            agent_result=agent_result,
                            started_at=start,
                            completed_at=step_end,
                        )
                    )

                current_step_start = None
                current_agent_name = None

            elif event.type == "output":
                final_conversation = event.data if event.data else []

        # If we didn't capture steps from executor events, parse the
        # final conversation for tool results.
        if not steps and final_conversation:
            steps = self._parse_conversation_steps(final_conversation)

        return steps

    @staticmethod
    def _extract_agent_result(
        event: Any,
        agent_name: str | None,
    ) -> AgentResult | None:
        """Build an ``AgentResult`` from an ``executor_completed`` event."""
        data = getattr(event, "data", None)
        name = agent_name or "UnknownAgent"

        # Try to get the response text / tool results
        if data is None:
            return AgentResult(
                agent_name=name,
                status=AgentStatus.SUCCESS,
                reasoning_summary="Step completed",
            )

        # If data is an AgentResponse, extract messages
        messages = getattr(data, "messages", None)
        if messages is None and hasattr(data, "text"):
            return AgentResult(
                agent_name=name,
                status=AgentStatus.SUCCESS,
                output=data.text,
                reasoning_summary=str(data.text)[:200] if data.text else "Completed",
            )

        # Parse function results from messages
        return MigrationOrchestrator._result_from_messages(
            messages or [],
            name,
        )

    @staticmethod
    def _result_from_messages(
        messages: list[Any],
        agent_name: str,
    ) -> AgentResult:
        """Parse tool call results and text from a message list."""
        tool_outputs: list[Any] = []
        reasoning = ""

        for msg in messages:
            if not hasattr(msg, "contents") or not msg.contents:
                continue
            for content in msg.contents:
                if getattr(content, "type", "") == "function_result":
                    raw = getattr(content, "result", "")
                    try:
                        parsed = json.loads(raw) if isinstance(raw, str) else raw
                    except (json.JSONDecodeError, TypeError):
                        parsed = raw
                    tool_outputs.append(parsed)
                elif getattr(content, "type", "") == "text":
                    text = getattr(content, "text", "")
                    if text:
                        reasoning = text

        output = tool_outputs[0] if len(tool_outputs) == 1 else (tool_outputs or None)
        status = AgentStatus.SUCCESS
        error_message: str | None = None

        # Check for failure indicators
        if isinstance(output, dict):
            if output.get("valid") is False:
                status = AgentStatus.PARTIAL
            if "error" in output:
                status = AgentStatus.FAILURE
                error_message = str(output["error"])

        return AgentResult(
            agent_name=agent_name,
            status=status,
            output=output,
            reasoning_summary=reasoning[:200] if reasoning else f"{agent_name} completed",
            error_message=error_message,
        )

    @staticmethod
    def _parse_conversation_steps(
        conversation: list[Any],
    ) -> list[StepResult]:
        """Fallback: parse the final conversation for tool results."""
        steps: list[StepResult] = []
        now = datetime.now(UTC)

        for msg in conversation:
            if not hasattr(msg, "contents") or not msg.contents:
                continue
            for content in msg.contents:
                if getattr(content, "type", "") == "function_result":
                    call_id = getattr(content, "call_id", "unknown")
                    raw = getattr(content, "result", "")
                    try:
                        parsed = json.loads(raw) if isinstance(raw, str) else raw
                    except (json.JSONDecodeError, TypeError):
                        parsed = raw

                    agent_result = AgentResult(
                        agent_name=call_id,
                        status=AgentStatus.SUCCESS,
                        output=parsed,
                        reasoning_summary=f"Tool result for {call_id}",
                    )
                    steps.append(
                        StepResult(
                            step_name=call_id,
                            agent_result=agent_result,
                            started_at=now,
                            completed_at=now,
                        )
                    )

        return steps
