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
import random
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from m2la_contracts.enums import InputMode

from m2la_agents.analyzer import AnalyzerAgent
from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentResult, AgentStatus, OrchestrationResult, StepResult
from m2la_agents.planner import PlannerAgent
from m2la_agents.repair_advisor import RepairAdvisorAgent
from m2la_agents.transformer import TransformerAgent
from m2la_agents.validator import ValidatorAgent

if TYPE_CHECKING:
    from agent_framework import Agent

logger = logging.getLogger(__name__)

_MAX_REASONING_SUMMARY_LEN = 200

# Default retry settings for transient Foundry / OpenAI errors
_DEFAULT_MAX_RETRIES = 3
_RETRY_BASE_DELAY_S = 1.0
_RETRY_MAX_DELAY_S = 10.0


def _is_retryable_error(exc: Exception) -> bool:
    """Return *True* if *exc* is a transient Foundry/OpenAI error worth retrying.

    The OpenAI Responses API occasionally returns a 400 with the message
    ``"No tool call found for function call output with call_id …"``
    when conversation context from one sequential agent leaks into the
    next.  Rebuilding the workflow and retrying typically resolves the
    issue because the new attempt starts with a fresh conversation state.

    We also retry on ``ChatClientException`` wrapping HTTP 429 (rate
    limit) or 5xx (server) status codes.
    """
    # agent_framework wraps OpenAI errors in ChatClientException
    try:
        from agent_framework.exceptions import ChatClientException
    except ImportError:  # pragma: no cover — defensive
        return False

    if not isinstance(exc, ChatClientException):
        return False

    msg = str(exc).lower()

    # The specific error from the problem statement
    if "no tool call found for function call output" in msg:
        return True

    # Rate limiting
    if "429" in msg or "rate limit" in msg:
        return True

    # Server errors (5xx)
    for code in ("500", "502", "503", "504"):
        if code in msg:
            return True

    return False


def _retry_delay(attempt: int) -> float:
    """Calculate exponential back-off delay with jitter.

    ``attempt`` is 0-indexed.  The delay doubles each attempt, capped at
    ``_RETRY_MAX_DELAY_S``, with ±25 % jitter to avoid thundering-herd
    effects across concurrent requests.
    """
    base = _RETRY_BASE_DELAY_S * (2**attempt)
    capped = min(base, _RETRY_MAX_DELAY_S)
    jitter = capped * random.uniform(0.75, 1.25)  # noqa: S311 — not security-sensitive
    return jitter


class MigrationOrchestrator:
    """Runs the full migration pipeline through a sequence of LLM-backed agents.

    Every migration request flows through the LLM via a
    ``SequentialBuilder`` workflow.  The ``client`` parameter (a
    ``FoundryChatClient`` or compatible) is **required**.

    Transient errors from the Foundry / OpenAI backend (e.g. orphaned
    tool-call IDs in the conversation context, rate limits, or 5xx
    responses) are automatically retried up to ``max_retries`` times
    with exponential back-off.

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
        max_retries: int = _DEFAULT_MAX_RETRIES,
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
        self.max_retries = max(0, max_retries)

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

        Transient Foundry / OpenAI errors are automatically retried up
        to ``self.max_retries`` times.  Each retry rebuilds the
        ``SequentialBuilder`` workflow from scratch so the conversation
        context starts fresh.
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

        # Construct user message describing the migration task
        mode_str = input_mode.value if input_mode else "auto-detect"
        user_message = (
            f"Migrate the MuleSoft project at: {input_path}\n"
            f"Input mode: {mode_str}\n"
            f"Output directory: {output_directory or 'default'}\n"
            f"Correlation ID: {cid}"
        )

        # Execute the workflow with retry logic
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
                self._execute_workflow_with_retries(user_message),
            )
            logger.info("Workflow completed with %d step(s)", len(step_results))
        except RuntimeError:
            raise  # Propagate loop-detection error
        except Exception:
            logger.exception("Workflow execution failed")
            raise

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

    def _build_workflow(self) -> Any:
        """Build a fresh ``SequentialBuilder`` workflow.

        A fresh workflow is created on every call so that the
        conversation context is clean — this avoids stale tool-call IDs
        from a previous attempt leaking into the new request.
        """
        from agent_framework.orchestrations import SequentialBuilder

        maf_agents: list[Agent] = []
        for agent in self.agents:
            maf_agent = agent.build_maf_agent(self.client)
            maf_agents.append(maf_agent)
            logger.info("Built MAF agent: %s", agent.name)

        return SequentialBuilder(participants=maf_agents).build()

    async def _execute_workflow_with_retries(
        self,
        user_message: str,
    ) -> list[StepResult]:
        """Execute the workflow, retrying on transient Foundry errors.

        On each attempt a **new** ``SequentialBuilder`` workflow is
        constructed so the conversation context starts fresh.  This is
        the key to resolving the "No tool call found for function call
        output" error — stale ``call_id`` references from a previous
        agent's tool invocations are not carried over.
        """
        last_exc: Exception | None = None

        for attempt in range(1 + self.max_retries):
            workflow = self._build_workflow()
            try:
                return await self._execute_workflow(workflow, user_message)
            except Exception as exc:
                if attempt < self.max_retries and _is_retryable_error(exc):
                    last_exc = exc
                    delay = _retry_delay(attempt)
                    logger.warning(
                        "Retryable Foundry error on attempt %d/%d, retrying in %.1fs: %s",
                        attempt + 1,
                        1 + self.max_retries,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

        # Should never reach here, but satisfy type checker
        raise last_exc  # type: ignore[misc]

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
        """
        final_conversation: list[Any] = []

        async for event in workflow.run(user_message, stream=True):
            if event.type == "output":
                final_conversation = event.data if event.data else []

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
