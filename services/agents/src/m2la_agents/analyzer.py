"""AnalyzerAgent — orchestrates Mule project/flow analysis.

Deterministic logic lives in:
    - ``m2la_parser.parse`` — XML parsing and project discovery
    - ``m2la_ir.builders``  — IR construction
    - ``m2la_validate.engine`` — input validation

This agent composes those services into a single step that:
1. Parses the MuleSoft input into a :class:`ProjectInventory`.
2. Builds the intermediate representation (:class:`MuleIR`).
3. Validates the Mule input.
4. Returns the IR, inventory, and validation report.
"""

from __future__ import annotations

import time
from pathlib import Path

from azure.ai.agents.models import FunctionTool
from m2la_contracts.enums import InputMode
from m2la_contracts.helpers import detect_input_mode
from m2la_ir.builders import (
    build_project_ir,
    build_single_flow_ir,
    make_flow,
    make_http_trigger,
    make_logger,
    make_processor,
    make_source_location,
)
from m2la_ir.enums import FlowKind, ProcessorType, TriggerType
from m2la_ir.models import Flow, MuleIR, Trigger
from m2la_parser.models import ProjectInventory
from m2la_parser.parse import parse
from m2la_validate.engine import validate_mule_input

from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus


def _inventory_to_ir(inventory: ProjectInventory, input_path: str) -> MuleIR:
    """Convert a parsed ProjectInventory into a MuleIR.

    This bridges the parser output (ProjectInventory with MuleFlows) to the
    IR layer (MuleIR with Flow/FlowStep nodes). The conversion extracts
    flow metadata and delegates to the IR builders for proper construction.
    """
    flows: list[Flow] = []
    for mule_flow in inventory.flows:
        trigger = None
        if mule_flow.trigger:
            ns = mule_flow.trigger.namespace or ""
            el = mule_flow.trigger.element_type
            if ns == "http" and el == "listener":
                path = mule_flow.trigger.attributes.get("path", "/")
                trigger = make_http_trigger(
                    path=path,
                    source_location=make_source_location(file=mule_flow.source_file),
                )
            else:
                trigger = Trigger(
                    type=TriggerType.UNKNOWN,
                    config={"namespace": ns, "element": el},
                    source_location=make_source_location(file=mule_flow.source_file),
                )

        steps = []
        for proc in mule_flow.processors:
            if proc.element_type == "logger":
                msg = proc.attributes.get("message", "")
                steps.append(make_logger(message=msg, source_location=make_source_location(file=mule_flow.source_file)))
            else:
                steps.append(
                    make_processor(
                        ProcessorType.GENERIC,
                        name=proc.element_type,
                        config=dict(proc.attributes),
                        source_location=make_source_location(file=mule_flow.source_file),
                    )
                )

        flow = make_flow(
            name=mule_flow.name,
            kind=FlowKind.FLOW,
            trigger=trigger,
            steps=steps,
            source_location=make_source_location(file=mule_flow.source_file),
        )
        flows.append(flow)

    for sub in inventory.subflows:
        steps = []
        for proc in sub.processors:
            steps.append(
                make_processor(
                    ProcessorType.GENERIC,
                    name=proc.element_type,
                    config=dict(proc.attributes),
                    source_location=make_source_location(file=sub.source_file),
                )
            )

        flow = make_flow(
            name=sub.name,
            kind=FlowKind.SUB_FLOW,
            steps=steps,
            source_location=make_source_location(file=sub.source_file),
        )
        flows.append(flow)

    warnings = list(inventory.warnings)

    if inventory.mode == InputMode.PROJECT:
        pm = inventory.project_metadata
        return build_project_ir(
            source_path=input_path,
            project_name=pm.artifact_id if pm else None,
            group_id=pm.group_id if pm else None,
            artifact_id=pm.artifact_id if pm else None,
            version=pm.version if pm else None,
            flows=flows,
            warnings=warnings,
        )
    else:
        return build_single_flow_ir(
            source_path=input_path,
            flows=flows,
            warnings=warnings,
        )


class AnalyzerAgent(BaseAgent):
    """Orchestrates Mule project/flow analysis.

    This agent composes the parser, IR builder, and input validator
    into a single analysis step. It does **not** contain any LLM logic;
    all processing is deterministic.

    The agent deposits the following keys into ``context.accumulated_data``:

    - ``"inventory"`` — the :class:`ProjectInventory` from the parser.
    - ``"ir"`` — the :class:`MuleIR` intermediate representation.
    - ``"input_validation"`` — the :class:`ValidationReport` for input.
    - ``"input_mode"`` — the resolved :class:`InputMode`.
    """

    def __init__(self) -> None:
        from m2la_agents.prompts import ANALYZER_PROMPT

        super().__init__(
            name="AnalyzerAgent",
            instructions=ANALYZER_PROMPT,
        )

    def _register_tools(self) -> None:
        """Register the ``analyze_mule_input`` function tool."""
        from m2la_agents.function_tools import analyze_mule_input

        functions = FunctionTool({analyze_mule_input})
        self.toolset.add(functions)

    def execute(self, context: AgentContext) -> AgentResult:
        """Parse, build IR, and validate the MuleSoft input.

        Args:
            context: Must have ``input_path`` set. ``input_mode`` is
                auto-detected if not provided.

        Returns:
            AgentResult with the IR and validation report as output.
        """
        start = time.monotonic()
        warnings: list[str] = []

        try:
            # 1. Resolve input mode
            mode = context.input_mode
            if mode is None:
                mode = detect_input_mode(context.input_path)

            # 2. Parse input → ProjectInventory
            inventory = parse(context.input_path, mode=mode)
            context.accumulated_data["inventory"] = inventory
            context.accumulated_data["input_mode"] = mode

            # 3. Build IR from inventory
            ir = _inventory_to_ir(inventory, context.input_path)
            context.accumulated_data["ir"] = ir

            # 4. Validate Mule input
            input_report = validate_mule_input(Path(context.input_path), mode)
            context.accumulated_data["input_validation"] = input_report

            # Collect parser warnings
            for w in inventory.warnings:
                warnings.append(f"{w.code}: {w.message}")

            # Collect validation warnings
            for issue in input_report.issues:
                warnings.append(f"{issue.rule_id}: {issue.message}")

            # Build reasoning summary
            flow_count = len(inventory.flows)
            subflow_count = len(inventory.subflows)
            total_constructs = sum(len(f.processors) for f in inventory.flows)
            summary_parts = [f"Parsed {flow_count} flow(s)"]
            if subflow_count > 0:
                summary_parts.append(f"{subflow_count} sub-flow(s)")
            summary_parts.append(f"with {total_constructs} construct(s)")
            if warnings:
                summary_parts.append(f"{len(warnings)} warning(s)")
            reasoning = ", ".join(summary_parts)

            elapsed_ms = (time.monotonic() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.SUCCESS,
                output={
                    "ir": ir,
                    "inventory": inventory,
                    "input_validation": input_report,
                    "mode": mode,
                },
                reasoning_summary=reasoning,
                duration_ms=elapsed_ms,
                warnings=warnings,
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILURE,
                reasoning_summary=f"Analysis failed: {exc}",
                duration_ms=elapsed_ms,
                warnings=warnings,
                error_message=str(exc),
            )
