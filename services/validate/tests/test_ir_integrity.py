"""Tests for IR integrity validation rules."""

from __future__ import annotations

from m2la_contracts.enums import InputMode, Severity
from m2la_ir.enums import (
    ErrorHandlerType,
    FlowKind,
    ProcessorType,
    RouterType,
    ScopeType,
    TriggerType,
)
from m2la_ir.models import (
    ErrorHandler,
    Flow,
    IRMetadata,
    MuleIR,
    Processor,
    ProjectMetadata,
    Route,
    Router,
    Scope,
    Trigger,
    VariableOperation,
)

from m2la_validate.rules.ir_integrity import validate_ir


def _make_ir(flows: list[Flow], mode: InputMode = InputMode.PROJECT) -> MuleIR:
    """Create a minimal MuleIR for testing."""
    return MuleIR(
        ir_metadata=IRMetadata(source_mode=mode, source_path="/test"),
        project_metadata=ProjectMetadata(),
        flows=flows,
    )


# ── Passing cases ─────────────────────────────────────────────────────────────


class TestIRIntegrityPassing:
    """Cases that should produce no issues."""

    def test_valid_flow_with_trigger(self) -> None:
        """A flow with a trigger and steps should be valid."""
        flow = Flow(
            kind=FlowKind.FLOW,
            name="myFlow",
            trigger=Trigger(type=TriggerType.HTTP_LISTENER),
            steps=[
                Processor(type=ProcessorType.SET_PAYLOAD, config={"value": "hello"}),
            ],
        )
        ir = _make_ir([flow])
        issues = validate_ir(ir)
        assert issues == []

    def test_valid_subflow(self) -> None:
        """A sub-flow without a trigger should be valid."""
        subflow = Flow(
            kind=FlowKind.SUB_FLOW,
            name="helperFlow",
            steps=[
                VariableOperation(operation="set", variable_name="x", value="1"),
            ],
        )
        ir = _make_ir([subflow])
        issues = validate_ir(ir)
        assert issues == []

    def test_flow_ref_to_existing_subflow(self) -> None:
        """Flow-ref targeting an existing sub-flow should be valid."""
        subflow = Flow(
            kind=FlowKind.SUB_FLOW,
            name="helper",
            steps=[
                Processor(type=ProcessorType.LOGGER, config={"message": "hi"}),
            ],
        )
        main_flow = Flow(
            kind=FlowKind.FLOW,
            name="main",
            trigger=Trigger(type=TriggerType.HTTP_LISTENER),
            steps=[
                Processor(
                    type=ProcessorType.FLOW_REF,
                    name="helper",
                    config={"name": "helper"},
                ),
            ],
        )
        ir = _make_ir([main_flow, subflow])
        issues = validate_ir(ir)
        assert issues == []

    def test_variable_set_then_remove(self) -> None:
        """Setting a variable then removing it should be valid."""
        flow = Flow(
            kind=FlowKind.FLOW,
            name="varFlow",
            trigger=Trigger(type=TriggerType.SCHEDULER),
            steps=[
                VariableOperation(operation="set", variable_name="temp", value="val"),
                VariableOperation(operation="remove", variable_name="temp"),
            ],
        )
        ir = _make_ir([flow])
        issues = validate_ir(ir)
        assert issues == []


# ── Failing cases ─────────────────────────────────────────────────────────────


class TestIRIntegrityFailing:
    """Cases that should produce issues."""

    def test_flow_without_trigger(self) -> None:
        """A top-level flow without a trigger should produce a warning."""
        flow = Flow(
            kind=FlowKind.FLOW,
            name="noTrigger",
            steps=[
                Processor(type=ProcessorType.LOGGER, config={"message": "test"}),
            ],
        )
        ir = _make_ir([flow])
        issues = validate_ir(ir)
        rule_ids = [i.rule_id for i in issues]
        assert "IR_001" in rule_ids

    def test_subflow_with_trigger(self) -> None:
        """A sub-flow with a trigger should produce a warning."""
        subflow = Flow(
            kind=FlowKind.SUB_FLOW,
            name="badSubflow",
            trigger=Trigger(type=TriggerType.HTTP_LISTENER),
            steps=[
                Processor(type=ProcessorType.LOGGER),
            ],
        )
        ir = _make_ir([subflow])
        issues = validate_ir(ir)
        rule_ids = [i.rule_id for i in issues]
        assert "IR_002" in rule_ids

    def test_empty_flow(self) -> None:
        """A flow with no steps and no trigger should produce a warning."""
        flow = Flow(kind=FlowKind.FLOW, name="empty")
        ir = _make_ir([flow])
        issues = validate_ir(ir)
        rule_ids = [i.rule_id for i in issues]
        assert "IR_003" in rule_ids

    def test_flow_ref_missing_target_project_mode(self) -> None:
        """Flow-ref to non-existent target in project mode should be an error."""
        flow = Flow(
            kind=FlowKind.FLOW,
            name="main",
            trigger=Trigger(type=TriggerType.HTTP_LISTENER),
            steps=[
                Processor(
                    type=ProcessorType.FLOW_REF,
                    name="nonExistent",
                    config={"name": "nonExistent"},
                ),
            ],
        )
        ir = _make_ir([flow], mode=InputMode.PROJECT)
        issues = validate_ir(ir)
        ref_issues = [i for i in issues if i.rule_id == "IR_010"]
        assert len(ref_issues) == 1
        assert ref_issues[0].severity == Severity.ERROR

    def test_flow_ref_missing_target_single_flow_mode(self) -> None:
        """Flow-ref to non-existent target in single-flow mode should be a warning."""
        flow = Flow(
            kind=FlowKind.FLOW,
            name="main",
            trigger=Trigger(type=TriggerType.HTTP_LISTENER),
            steps=[
                Processor(
                    type=ProcessorType.FLOW_REF,
                    name="external",
                    config={"name": "external"},
                ),
            ],
        )
        ir = _make_ir([flow], mode=InputMode.SINGLE_FLOW)
        issues = validate_ir(ir)
        ref_issues = [i for i in issues if i.rule_id == "IR_010"]
        assert len(ref_issues) == 1
        assert ref_issues[0].severity == Severity.WARNING

    def test_variable_removed_before_set(self) -> None:
        """Removing a variable that was never set should produce a warning."""
        flow = Flow(
            kind=FlowKind.FLOW,
            name="varFlow",
            trigger=Trigger(type=TriggerType.SCHEDULER),
            steps=[
                VariableOperation(operation="remove", variable_name="unset"),
            ],
        )
        ir = _make_ir([flow])
        issues = validate_ir(ir)
        rule_ids = [i.rule_id for i in issues]
        assert "IR_011" in rule_ids

    def test_nested_flow_ref_in_router(self) -> None:
        """Flow-ref inside a router route should still be validated."""
        flow = Flow(
            kind=FlowKind.FLOW,
            name="routerFlow",
            trigger=Trigger(type=TriggerType.HTTP_LISTENER),
            steps=[
                Router(
                    type=RouterType.CHOICE,
                    routes=[
                        Route(
                            condition="true",
                            steps=[
                                Processor(
                                    type=ProcessorType.FLOW_REF,
                                    name="missing",
                                    config={"name": "missing"},
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        ir = _make_ir([flow])
        issues = validate_ir(ir)
        ref_issues = [i for i in issues if i.rule_id == "IR_010"]
        assert len(ref_issues) == 1

    def test_nested_flow_ref_in_scope(self) -> None:
        """Flow-ref inside a scope should still be validated."""
        flow = Flow(
            kind=FlowKind.FLOW,
            name="scopeFlow",
            trigger=Trigger(type=TriggerType.HTTP_LISTENER),
            steps=[
                Scope(
                    type=ScopeType.FOREACH,
                    steps=[
                        Processor(
                            type=ProcessorType.FLOW_REF,
                            name="missing",
                            config={"name": "missing"},
                        ),
                    ],
                ),
            ],
        )
        ir = _make_ir([flow])
        issues = validate_ir(ir)
        ref_issues = [i for i in issues if i.rule_id == "IR_010"]
        assert len(ref_issues) == 1

    def test_error_handler_steps_validated(self) -> None:
        """Steps inside error handlers should be validated."""
        flow = Flow(
            kind=FlowKind.FLOW,
            name="errorFlow",
            trigger=Trigger(type=TriggerType.HTTP_LISTENER),
            steps=[],
            error_handlers=[
                ErrorHandler(
                    type=ErrorHandlerType.ON_ERROR_CONTINUE,
                    steps=[
                        Processor(
                            type=ProcessorType.FLOW_REF,
                            name="missing",
                            config={"name": "missing"},
                        ),
                    ],
                ),
            ],
        )
        ir = _make_ir([flow])
        issues = validate_ir(ir)
        ref_issues = [i for i in issues if i.rule_id == "IR_010"]
        assert len(ref_issues) == 1

    def test_all_issues_have_remediation_hints(self) -> None:
        """All IR issues should include remediation hints."""
        flow = Flow(kind=FlowKind.FLOW, name="empty")
        ir = _make_ir([flow])
        issues = validate_ir(ir)
        assert len(issues) > 0
        for issue in issues:
            assert issue.remediation_hint is not None
