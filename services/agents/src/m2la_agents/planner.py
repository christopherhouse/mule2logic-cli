"""PlannerAgent — creates a migration plan from analysis results.

Deterministic logic lives in:
    - ``m2la_mapping_config.loader``   — loads connector/construct YAML configs
    - ``m2la_mapping_config.resolver`` — resolves MuleSoft elements to Logic Apps equivalents

This agent examines the MuleIR produced by :class:`AnalyzerAgent`, checks
mapping availability for each construct, and produces a structured
:class:`MigrationPlan`.
"""

from __future__ import annotations

import time

from m2la_ir.models import (
    ConnectorOperation,
    Flow,
    FlowStep,
    MuleIR,
    Processor,
    Router,
    Scope,
    Transform,
    VariableOperation,
)
from m2la_mapping_config.loader import load_all
from m2la_mapping_config.resolver import MappingResolver

from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus, MappingDecision, MigrationPlan


def _collect_constructs(flows: list[Flow]) -> list[str]:
    """Recursively collect all construct element names from flows.

    Returns a flat list of element names (with duplicates) representing
    every step across all flows.
    """
    elements: list[str] = []

    def _scan_steps(steps: list[FlowStep]) -> None:
        for step in steps:
            if isinstance(step, Processor):
                elements.append(step.type.value)
            elif isinstance(step, VariableOperation):
                elements.append(f"variable_{step.operation}")
            elif isinstance(step, Transform):
                elements.append(step.type.value)
            elif isinstance(step, ConnectorOperation):
                elements.append(step.connector_type.value)
            elif isinstance(step, Router):
                elements.append(step.type.value)
                for route in step.routes:
                    _scan_steps(route.steps)
                if step.default_route:
                    _scan_steps(step.default_route.steps)
            elif isinstance(step, Scope):
                elements.append(step.type.value)
                _scan_steps(step.steps)

    for flow in flows:
        if flow.trigger:
            elements.append(flow.trigger.type.value)
        _scan_steps(flow.steps)

    return elements


class PlannerAgent(BaseAgent):
    """Creates a migration plan by evaluating mapping availability.

    Takes the :class:`MuleIR` from the analyzer output, loads the
    mapping configuration, and produces a :class:`MigrationPlan` that
    describes which constructs are supported, unsupported, or partially
    supported.

    The agent deposits the following keys into ``context.accumulated_data``:

    - ``"migration_plan"`` — the :class:`MigrationPlan`.
    - ``"mapping_config"`` — the loaded :class:`MappingConfig`.
    """

    def __init__(self) -> None:
        from m2la_agents.prompts import planner_prompt

        super().__init__(
            name="PlannerAgent",
            instructions=planner_prompt(),
        )

    def _get_tools(self):  # noqa: ANN201
        """Return the ``create_migration_plan`` function as a tool."""
        from m2la_agents.function_tools import create_migration_plan

        return [create_migration_plan]

    def execute(self, context: AgentContext) -> AgentResult:
        """Produce a migration plan from the analysis results.

        Expects ``context.accumulated_data["ir"]`` to contain a :class:`MuleIR`.

        Args:
            context: Must have ``"ir"`` in accumulated_data.

        Returns:
            AgentResult with the :class:`MigrationPlan` as output.
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

            # Load mapping config
            try:
                mapping_config = load_all()
            except FileNotFoundError as exc:
                warnings.append(f"Mapping config not fully loaded: {exc}")
                mapping_config = None

            context.accumulated_data["mapping_config"] = mapping_config

            # Collect all constructs from the IR
            construct_names = _collect_constructs(ir.flows)

            # Count per construct type
            construct_summary: dict[str, int] = {}
            for name in construct_names:
                construct_summary[name] = construct_summary.get(name, 0) + 1

            # Evaluate mapping availability
            supported = 0
            unsupported = 0
            partial = 0
            decisions: list[MappingDecision] = []

            if mapping_config is not None:
                resolver = MappingResolver(mapping_config)
                seen: set[str] = set()

                for element_name in construct_names:
                    if element_name in seen:
                        continue
                    seen.add(element_name)

                    construct_entry = resolver.resolve_construct(element_name)
                    if construct_entry is not None:
                        if construct_entry.supported:
                            supported += construct_summary.get(element_name, 0)
                            decisions.append(
                                MappingDecision(
                                    mule_element=element_name,
                                    status="supported",
                                    logic_apps_equivalent=construct_entry.logic_apps_type,
                                    notes=construct_entry.notes,
                                )
                            )
                        else:
                            partial += construct_summary.get(element_name, 0)
                            decisions.append(
                                MappingDecision(
                                    mule_element=element_name,
                                    status="partial",
                                    logic_apps_equivalent=construct_entry.logic_apps_type,
                                    notes=construct_entry.notes,
                                )
                            )
                    else:
                        unsupported += construct_summary.get(element_name, 0)
                        decisions.append(
                            MappingDecision(
                                mule_element=element_name,
                                status="unsupported",
                            )
                        )
            else:
                # No mapping config — mark everything as unsupported
                for element_name, count in construct_summary.items():
                    unsupported += count
                    decisions.append(
                        MappingDecision(
                            mule_element=element_name,
                            status="unsupported",
                            notes="Mapping config unavailable",
                        )
                    )

            plan = MigrationPlan(
                flow_count=len(ir.flows),
                construct_summary=construct_summary,
                supported_count=supported,
                unsupported_count=unsupported,
                partial_count=partial,
                mapping_decisions=decisions,
                estimated_gaps=unsupported + partial,
            )
            context.accumulated_data["migration_plan"] = plan

            # Build reasoning summary
            reasoning = (
                f"Plan for {plan.flow_count} flow(s): "
                f"{supported} supported, {unsupported} unsupported, {partial} partial. "
                f"Estimated {plan.estimated_gaps} gap(s)."
            )

            elapsed_ms = (time.monotonic() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.SUCCESS,
                output=plan,
                reasoning_summary=reasoning,
                duration_ms=elapsed_ms,
                warnings=warnings,
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILURE,
                reasoning_summary=f"Planning failed: {exc}",
                duration_ms=elapsed_ms,
                warnings=warnings,
                error_message=str(exc),
            )
