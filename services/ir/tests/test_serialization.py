"""Tests: JSON serialization roundtrip for all node types and edge cases."""

import json

from m2la_contracts.common import Warning
from m2la_contracts.enums import InputMode, Severity

from m2la_ir import (
    ErrorHandlerType,
    ScopeType,
    build_project_ir,
    build_single_flow_ir,
    from_json,
    make_choice_router,
    make_dataweave_transform,
    make_db_operation,
    make_error_handler,
    make_flow,
    make_foreach_scope,
    make_http_request,
    make_http_trigger,
    make_logger,
    make_remove_variable,
    make_route,
    make_scheduler_trigger,
    make_set_variable,
    make_source_location,
    make_try_scope,
    to_json,
)
from m2la_ir.models import (
    ConnectorOperation,
    Processor,
    Router,
    Scope,
    Transform,
    VariableOperation,
)


def test_roundtrip_all_step_types():
    """Verify JSON roundtrip preserves all step types in a single flow."""
    steps = [
        make_logger(message="hello"),
        make_set_variable(variable_name="x", value="#[1]"),
        make_remove_variable(variable_name="y"),
        make_dataweave_transform(expression="%dw 2.0\n---\npayload"),
        make_http_request(method="GET", url="/test"),
        make_db_operation(operation="select", query="SELECT 1"),
        make_choice_router(
            routes=[make_route(condition="#[true]", steps=[make_logger(message="in route")])],
            default_route=make_route(steps=[make_logger(message="default")]),
        ),
        make_foreach_scope(collection="#[payload]", steps=[make_logger(message="loop")]),
    ]

    flow = make_flow(name="all-types", trigger=make_http_trigger(), steps=steps)
    ir = build_project_ir(source_path="/test", flows=[flow])

    json_str = to_json(ir)
    restored = from_json(json_str)

    assert len(restored.flows[0].steps) == len(steps)

    expected_types = [
        "processor",
        "variable_operation",
        "variable_operation",
        "transform",
        "connector_operation",
        "connector_operation",
        "router",
        "scope",
    ]
    for step, expected in zip(restored.flows[0].steps, expected_types, strict=True):
        assert step.step_type == expected


def test_roundtrip_preserves_model_types():
    """Verify deserialized objects are the correct Pydantic model types."""
    steps = [
        make_logger(message="test"),
        make_set_variable(variable_name="v", value="1"),
        make_dataweave_transform(expression="payload"),
        make_http_request(method="GET"),
        make_choice_router(),
        make_foreach_scope(),
    ]

    flow = make_flow(name="typed", trigger=make_http_trigger(), steps=steps)
    ir = build_project_ir(source_path="/test", flows=[flow])

    restored = from_json(to_json(ir))
    s = restored.flows[0].steps

    assert isinstance(s[0], Processor)
    assert isinstance(s[1], VariableOperation)
    assert isinstance(s[2], Transform)
    assert isinstance(s[3], ConnectorOperation)
    assert isinstance(s[4], Router)
    assert isinstance(s[5], Scope)


def test_roundtrip_empty_flows():
    """Verify roundtrip with no flows."""
    ir = build_project_ir(source_path="/empty")
    json_str = to_json(ir)
    restored = from_json(json_str)

    assert len(restored.flows) == 0
    assert restored.ir_metadata.source_mode == InputMode.PROJECT


def test_roundtrip_empty_steps():
    """Verify roundtrip with a flow that has no steps."""
    flow = make_flow(name="empty-flow", trigger=make_http_trigger())
    ir = build_project_ir(source_path="/test", flows=[flow])

    restored = from_json(to_json(ir))
    assert len(restored.flows[0].steps) == 0


def test_roundtrip_nested_scopes():
    """Verify roundtrip with nested scopes (foreach inside try)."""
    inner_foreach = make_foreach_scope(
        collection="#[payload.items]",
        steps=[make_logger(message="processing item")],
    )
    try_scope = make_try_scope(steps=[inner_foreach])
    flow = make_flow(name="nested", trigger=make_scheduler_trigger(), steps=[try_scope])
    ir = build_project_ir(source_path="/test", flows=[flow])

    restored = from_json(to_json(ir))
    outer = restored.flows[0].steps[0]
    assert outer.step_type == "scope"
    assert outer.type == ScopeType.TRY_SCOPE

    inner = outer.steps[0]
    assert inner.step_type == "scope"
    assert inner.type == ScopeType.FOREACH
    assert len(inner.steps) == 1


def test_roundtrip_error_handlers():
    """Verify error handlers survive JSON roundtrip."""
    eh = make_error_handler(
        handler_type=ErrorHandlerType.ON_ERROR_PROPAGATE,
        error_type="MULE:CONNECTIVITY",
        steps=[make_logger(message="error!")],
    )
    flow = make_flow(
        name="with-errors",
        trigger=make_http_trigger(),
        error_handlers=[eh],
    )
    ir = build_project_ir(source_path="/test", flows=[flow])

    restored = from_json(to_json(ir))
    assert len(restored.flows[0].error_handlers) == 1
    assert restored.flows[0].error_handlers[0].type == ErrorHandlerType.ON_ERROR_PROPAGATE
    assert restored.flows[0].error_handlers[0].error_type == "MULE:CONNECTIVITY"


def test_roundtrip_source_locations():
    """Verify source locations survive JSON roundtrip."""
    loc = make_source_location("test.xml", line=42, column=8)
    flow = make_flow(
        name="located",
        trigger=make_http_trigger(source_location=loc),
        steps=[make_logger(message="test", source_location=loc)],
        source_location=loc,
    )
    ir = build_project_ir(source_path="/test", flows=[flow])

    restored = from_json(to_json(ir))
    f = restored.flows[0]
    assert f.source_location.file == "test.xml"
    assert f.source_location.line == 42
    assert f.source_location.column == 8
    assert f.trigger.source_location.line == 42
    assert f.steps[0].source_location.line == 42


def test_roundtrip_warnings():
    """Verify warnings survive JSON roundtrip."""
    warnings = [
        Warning(
            code="TEST_WARNING",
            message="This is a test warning",
            severity=Severity.INFO,
        ),
    ]
    ir = build_single_flow_ir(source_path="/test.xml", warnings=warnings)

    restored = from_json(to_json(ir))
    assert len(restored.warnings) == 1
    assert restored.warnings[0].code == "TEST_WARNING"
    assert restored.warnings[0].severity == Severity.INFO


def test_json_is_valid_json():
    """Verify to_json produces valid, parseable JSON."""
    ir = build_project_ir(
        source_path="/test",
        project_name="test",
        flows=[make_flow(name="f", trigger=make_http_trigger())],
    )
    json_str = to_json(ir)
    parsed = json.loads(json_str)

    assert isinstance(parsed, dict)
    assert "ir_metadata" in parsed
    assert "flows" in parsed


def test_json_indentation():
    """Verify to_json uses 2-space indentation."""
    ir = build_project_ir(source_path="/test")
    json_str = to_json(ir)

    # Check that we have indented JSON (not compact)
    lines = json_str.split("\n")
    assert len(lines) > 1
    # Find a line with indentation
    indented = [line for line in lines if line.startswith("  ")]
    assert len(indented) > 0
