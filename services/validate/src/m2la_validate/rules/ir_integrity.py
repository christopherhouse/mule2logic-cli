"""IR integrity validation rules.

Validates the consistency and correctness of a MuleIR intermediate representation.
"""

from __future__ import annotations

from m2la_contracts.enums import InputMode, Severity, ValidationCategory
from m2la_contracts.validate import ValidationIssue
from m2la_ir.enums import FlowKind, ProcessorType
from m2la_ir.models import (
    Flow,
    FlowStep,
    MuleIR,
    Processor,
    Router,
    Scope,
    VariableOperation,
)


def validate_ir(ir: MuleIR) -> list[ValidationIssue]:
    """Validate IR integrity.

    Checks:
    - Every top-level flow has a trigger
    - Sub-flows do NOT have triggers
    - Flow-ref processors reference existing flows or sub-flows
    - Variables are set before being referenced (best-effort within a flow)
    - No empty flows (at least one step or trigger)
    - In single-flow mode, unresolvable flow-ref references are warnings
    """
    issues: list[ValidationIssue] = []
    is_single_flow = ir.ir_metadata.source_mode == InputMode.SINGLE_FLOW

    flow_names = {flow.name for flow in ir.flows}

    for flow in ir.flows:
        _validate_flow(flow, flow_names, is_single_flow, issues)

    return issues


def _validate_flow(
    flow: Flow,
    all_flow_names: set[str],
    is_single_flow: bool,
    issues: list[ValidationIssue],
) -> None:
    """Validate a single flow or sub-flow."""
    flow_loc = f"flow:{flow.name}"

    # Check trigger presence
    if flow.kind == FlowKind.FLOW and flow.trigger is None:
        issues.append(
            ValidationIssue(
                rule_id="IR_001",
                message=f"Flow '{flow.name}' has no trigger",
                severity=Severity.WARNING,
                category=ValidationCategory.IR_INTEGRITY,
                location=flow_loc,
                remediation_hint="Add a trigger (e.g., HTTP listener or scheduler) to the flow.",
            )
        )

    if flow.kind == FlowKind.SUB_FLOW and flow.trigger is not None:
        issues.append(
            ValidationIssue(
                rule_id="IR_002",
                message=f"Sub-flow '{flow.name}' should not have a trigger",
                severity=Severity.WARNING,
                category=ValidationCategory.IR_INTEGRITY,
                location=flow_loc,
                remediation_hint="Remove the trigger from the sub-flow; sub-flows are invoked via flow-ref.",
            )
        )

    # Empty flow check
    if not flow.steps and flow.trigger is None:
        issues.append(
            ValidationIssue(
                rule_id="IR_003",
                message=f"Flow '{flow.name}' has no steps and no trigger",
                severity=Severity.WARNING,
                category=ValidationCategory.IR_INTEGRITY,
                location=flow_loc,
                remediation_hint="Add at least one step or trigger to the flow.",
            )
        )

    # Check flow-ref targets and variable usage
    set_variables: set[str] = set()
    _validate_steps(flow.steps, all_flow_names, is_single_flow, flow_loc, set_variables, issues)

    # Also validate error handler steps
    for handler in flow.error_handlers:
        handler_loc = f"{flow_loc}/error-handler:{handler.type}"
        _validate_steps(handler.steps, all_flow_names, is_single_flow, handler_loc, set(set_variables), issues)


def _validate_steps(
    steps: list[FlowStep],
    all_flow_names: set[str],
    is_single_flow: bool,
    parent_loc: str,
    set_variables: set[str],
    issues: list[ValidationIssue],
) -> None:
    """Validate a list of flow steps recursively."""
    for step in steps:
        if isinstance(step, Processor):
            _validate_processor(step, all_flow_names, is_single_flow, parent_loc, issues)
        elif isinstance(step, VariableOperation):
            _validate_variable_op(step, parent_loc, set_variables, issues)
        elif isinstance(step, Router):
            _validate_router(step, all_flow_names, is_single_flow, parent_loc, set_variables, issues)
        elif isinstance(step, Scope):
            _validate_scope(step, all_flow_names, is_single_flow, parent_loc, set_variables, issues)


def _validate_processor(
    proc: Processor,
    all_flow_names: set[str],
    is_single_flow: bool,
    parent_loc: str,
    issues: list[ValidationIssue],
) -> None:
    """Validate a processor step."""
    if proc.type == ProcessorType.FLOW_REF:
        target = proc.config.get("name") or proc.name
        if target and target not in all_flow_names:
            severity = Severity.WARNING if is_single_flow else Severity.ERROR
            issues.append(
                ValidationIssue(
                    rule_id="IR_010",
                    message=f"Flow-ref target '{target}' not found in IR",
                    severity=severity,
                    category=ValidationCategory.IR_INTEGRITY,
                    location=parent_loc,
                    remediation_hint=(
                        f"Ensure the flow or sub-flow '{target}' exists. "
                        "In single-flow mode, external flow references produce warnings."
                    )
                    if is_single_flow
                    else f"Add the missing flow or sub-flow '{target}' to the project.",
                )
            )


def _validate_variable_op(
    var_op: VariableOperation,
    parent_loc: str,
    set_variables: set[str],
    issues: list[ValidationIssue],
) -> None:
    """Track variable set/remove operations."""
    if var_op.operation == "set":
        set_variables.add(var_op.variable_name)
    elif var_op.operation == "remove":
        if var_op.variable_name not in set_variables:
            issues.append(
                ValidationIssue(
                    rule_id="IR_011",
                    message=f"Variable '{var_op.variable_name}' removed but never set in this flow",
                    severity=Severity.WARNING,
                    category=ValidationCategory.IR_INTEGRITY,
                    location=parent_loc,
                    remediation_hint=(
                        f"Variable '{var_op.variable_name}' may be set in a prior flow or sub-flow. "
                        "Verify it is initialized before removal."
                    ),
                )
            )


def _validate_router(
    router: Router,
    all_flow_names: set[str],
    is_single_flow: bool,
    parent_loc: str,
    set_variables: set[str],
    issues: list[ValidationIssue],
) -> None:
    """Validate a router and its routes recursively."""
    router_loc = f"{parent_loc}/router:{router.type}"
    for route in router.routes:
        _validate_steps(route.steps, all_flow_names, is_single_flow, router_loc, set(set_variables), issues)
    if router.default_route:
        _validate_steps(
            router.default_route.steps, all_flow_names, is_single_flow, router_loc, set(set_variables), issues
        )


def _validate_scope(
    scope: Scope,
    all_flow_names: set[str],
    is_single_flow: bool,
    parent_loc: str,
    set_variables: set[str],
    issues: list[ValidationIssue],
) -> None:
    """Validate a scope and its nested steps recursively."""
    scope_loc = f"{parent_loc}/scope:{scope.type}"
    _validate_steps(scope.steps, all_flow_names, is_single_flow, scope_loc, set(set_variables), issues)
