"""ValidatorAgent — orchestrates output validation.

Deterministic logic lives in:
    - ``m2la_validate.engine.validate_output`` — output integrity checks

This agent validates the generated Logic Apps artifacts and produces
a structured :class:`ValidationReport`.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from azure.ai.agents.models import FunctionTool
from m2la_contracts.enums import InputMode
from m2la_contracts.validate import ValidationReport
from m2la_validate.engine import validate_output

from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus


class ValidatorAgent(BaseAgent):
    """Orchestrates validation of generated Logic Apps artifacts.

    Takes the transformation output and validates it against the output
    integrity rules.

    The agent deposits the following keys into ``context.accumulated_data``:

    - ``"output_validation"`` — the :class:`ValidationReport`.
    """

    def __init__(self) -> None:
        from m2la_agents.prompts import VALIDATOR_PROMPT

        super().__init__(
            name="ValidatorAgent",
            instructions=VALIDATOR_PROMPT,
        )

    def _register_tools(self) -> None:
        """Register the ``validate_output_artifacts`` function tool."""
        from m2la_agents.function_tools import validate_output_artifacts

        functions = FunctionTool({validate_output_artifacts})
        self.toolset.add(functions)

    def execute(self, context: AgentContext) -> AgentResult:
        """Validate the generated Logic Apps artifacts.

        Expects ``context.accumulated_data["transform_output"]`` and
        ``context.accumulated_data["input_mode"]``.

        For project mode, expects the output directory in ``context.output_directory``.
        For single-flow mode, expects the workflow dict in ``transform_output``.

        Args:
            context: Must have ``"transform_output"`` and ``"input_mode"``
                in accumulated_data.

        Returns:
            AgentResult with the :class:`ValidationReport` as output.
        """
        start = time.monotonic()
        warnings: list[str] = []

        try:
            transform_output = context.accumulated_data.get("transform_output")
            mode: InputMode = context.accumulated_data.get("input_mode", InputMode.PROJECT)

            if transform_output is None:
                elapsed_ms = (time.monotonic() - start) * 1000
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.FAILURE,
                    reasoning_summary="No transform output found — TransformerAgent must run first",
                    duration_ms=elapsed_ms,
                    error_message="Missing 'transform_output' in accumulated_data",
                )

            # Determine what to validate
            output_target: Path | dict[str, Any]
            if mode == InputMode.PROJECT:
                output_dir = context.output_directory or "output"
                output_target = Path(output_dir)
            else:
                # Single-flow mode: validate the workflow dict directly
                if isinstance(transform_output, dict):
                    output_target = transform_output
                elif hasattr(transform_output, "workflows"):
                    # ProjectArtifacts in single-flow mode shouldn't happen,
                    # but handle gracefully
                    first_wf = next(iter(transform_output.workflows.values()), {})
                    output_target = first_wf
                else:
                    output_target = {}

            # Run validation
            report: ValidationReport = validate_output(output_target, mode)
            context.accumulated_data["output_validation"] = report

            for issue in report.issues:
                warnings.append(f"{issue.rule_id}: {issue.message}")

            # Build reasoning summary
            if report.valid:
                summary = f"Validation passed — {report.artifacts_validated} artifact(s) checked, no issues"
            else:
                error_count = len([i for i in report.issues if i.severity.value in ("error", "critical")])
                warn_count = len(report.issues) - error_count
                summary = (
                    f"Validation found {len(report.issues)} issue(s) "
                    f"({error_count} error(s), {warn_count} warning(s)) "
                    f"across {report.artifacts_validated} artifact(s)"
                )

            status = AgentStatus.SUCCESS if report.valid else AgentStatus.PARTIAL

            elapsed_ms = (time.monotonic() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status=status,
                output=report,
                reasoning_summary=summary,
                duration_ms=elapsed_ms,
                warnings=warnings,
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILURE,
                reasoning_summary=f"Validation failed: {exc}",
                duration_ms=elapsed_ms,
                warnings=warnings,
                error_message=str(exc),
            )
