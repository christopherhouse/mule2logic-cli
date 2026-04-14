"""TransformerAgent — orchestrates IR → Logic Apps conversion.

Deterministic logic lives in:
    - ``m2la_transform.generator``        — full project generation
    - ``m2la_transform.single_flow``      — single-flow generation
    - ``m2la_validate.engine.validate_ir`` — IR validation before transform

This agent validates the IR, then delegates to the appropriate
transform function based on input mode.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from azure.ai.agents.models import FunctionTool
from m2la_contracts.enums import InputMode
from m2la_ir.models import MuleIR
from m2la_transform.generator import generate_project
from m2la_transform.single_flow import generate_single_flow_workflow
from m2la_validate.engine import validate_ir

from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus


class TransformerAgent(BaseAgent):
    """Orchestrates IR → Logic Apps artifact generation.

    Validates the IR before transformation, then generates Logic Apps
    artifacts using the deterministic transform services.

    The agent deposits the following keys into ``context.accumulated_data``:

    - ``"transform_output"`` — :class:`ProjectArtifacts` (project mode) or
      workflow ``dict`` (single-flow mode).
    - ``"migration_gaps"``   — list of :class:`MigrationGap` objects.
    - ``"ir_validation"``    — :class:`ValidationReport` from IR validation.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TransformerAgent",
            instructions=(
                "You are a transformation agent for MuleSoft to Logic Apps migration. "
                "Use the transform_to_logic_apps tool to convert intermediate "
                "representation into Logic Apps Standard artifacts."
            ),
        )

    def _register_tools(self) -> None:
        """Register the ``transform_to_logic_apps`` function tool."""
        from m2la_agents.function_tools import transform_to_logic_apps

        functions = FunctionTool({transform_to_logic_apps})
        self.toolset.add(functions)

    def execute(self, context: AgentContext) -> AgentResult:
        """Validate the IR and generate Logic Apps artifacts.

        Expects ``context.accumulated_data["ir"]`` to contain a :class:`MuleIR`
        and ``context.accumulated_data["input_mode"]`` to be set.

        Args:
            context: Must have ``"ir"`` and ``"input_mode"`` in accumulated_data.

        Returns:
            AgentResult with the generated artifacts and gaps as output.
        """
        start = time.monotonic()
        warnings: list[str] = []

        try:
            ir: MuleIR | None = context.accumulated_data.get("ir")
            if ir is None:
                elapsed_ms = (time.monotonic() - start) * 1000
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.FAILURE,
                    reasoning_summary="No IR found in context — AnalyzerAgent must run first",
                    duration_ms=elapsed_ms,
                    error_message="Missing 'ir' in accumulated_data",
                )

            mode: InputMode = context.accumulated_data.get("input_mode", ir.ir_metadata.source_mode)

            # 1. Validate IR before transformation
            ir_report = validate_ir(ir)
            context.accumulated_data["ir_validation"] = ir_report

            for issue in ir_report.issues:
                warnings.append(f"IR: {issue.rule_id}: {issue.message}")

            if not ir_report.valid:
                elapsed_ms = (time.monotonic() - start) * 1000
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.PARTIAL,
                    output={"ir_validation": ir_report},
                    reasoning_summary=f"IR validation found {len(ir_report.issues)} issue(s); proceeding with caution",
                    duration_ms=elapsed_ms,
                    warnings=warnings,
                )

            # 2. Generate artifacts
            output: Any
            gaps: list[Any]

            if mode == InputMode.PROJECT:
                output_dir = Path(context.output_directory) if context.output_directory else Path("output")
                output, gaps = generate_project(ir, output_dir)
            else:
                if ir.flows:
                    output, gaps = generate_single_flow_workflow(ir.flows[0])
                else:
                    output = {}
                    gaps = []
                    warnings.append("No flows found in IR for single-flow transformation")

            context.accumulated_data["transform_output"] = output
            context.accumulated_data["migration_gaps"] = gaps

            # 3. Build reasoning summary
            gap_count = len(gaps)
            if mode == InputMode.PROJECT:
                workflow_count = len(output.workflows) if hasattr(output, "workflows") else 0
                summary = f"Generated {workflow_count} workflow(s)"
            else:
                summary = "Generated 1 workflow"

            if gap_count > 0:
                summary += f" with {gap_count} migration gap(s)"
            else:
                summary += " with no migration gaps"

            status = AgentStatus.SUCCESS if gap_count == 0 else AgentStatus.PARTIAL

            elapsed_ms = (time.monotonic() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status=status,
                output={"artifacts": output, "gaps": gaps},
                reasoning_summary=summary,
                duration_ms=elapsed_ms,
                warnings=warnings,
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILURE,
                reasoning_summary=f"Transformation failed: {exc}",
                duration_ms=elapsed_ms,
                warnings=warnings,
                error_message=str(exc),
            )
