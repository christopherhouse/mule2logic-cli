"""Tests: Single-flow mode — standalone XML with no project context.

This validates that the IR correctly represents a single flow file with
no pom.xml, no project metadata, and appropriate warnings for unresolvable
external references.
"""

from m2la_contracts.common import Warning
from m2la_contracts.enums import InputMode, Severity

from m2la_ir import (
    FlowKind,
    TriggerType,
    build_single_flow_ir,
    from_json,
    make_dataweave_transform,
    make_flow,
    make_http_request,
    make_http_trigger,
    make_logger,
    make_source_location,
    to_json,
)


def _build_single_flow_ir():
    """Build an IR for a standalone flow XML with missing external references."""
    trigger = make_http_trigger(
        path="/api/items",
        method="GET",
        config_ref="HTTP_Listener_config",
        source_location=make_source_location("standalone-flow.xml", line=3),
    )

    transform = make_dataweave_transform(
        expression="%dw 2.0\noutput application/json\n---\npayload",
        source_location=make_source_location("standalone-flow.xml", line=8),
    )

    outbound = make_http_request(
        method="GET",
        url="${backend.url}/items",
        config_ref="HTTP_Request_config",
        source_location=make_source_location("standalone-flow.xml", line=15),
    )

    flow = make_flow(
        name="items-flow",
        trigger=trigger,
        steps=[transform, outbound],
        source_location=make_source_location("standalone-flow.xml", line=2),
    )

    sub_flow = make_flow(
        name="items-helper",
        kind=FlowKind.SUB_FLOW,
        steps=[
            make_logger(
                message="Helper sub-flow",
                source_location=make_source_location("standalone-flow.xml", line=25),
            ),
        ],
        source_location=make_source_location("standalone-flow.xml", line=23),
    )

    # Warnings for unresolvable external references
    warnings = [
        Warning(
            code="MISSING_CONNECTOR_CONFIG",
            message="Connector config 'HTTP_Listener_config' not found — no project context available",
            severity=Severity.WARNING,
            source_location="standalone-flow.xml:3",
        ),
        Warning(
            code="MISSING_CONNECTOR_CONFIG",
            message="Connector config 'HTTP_Request_config' not found — no project context available",
            severity=Severity.WARNING,
            source_location="standalone-flow.xml:15",
        ),
        Warning(
            code="UNRESOLVABLE_PROPERTY",
            message="Property placeholder '${backend.url}' cannot be resolved — no property files available",
            severity=Severity.WARNING,
            source_location="standalone-flow.xml:15",
        ),
    ]

    return build_single_flow_ir(
        source_path="/tmp/standalone-flow.xml",
        flows=[flow, sub_flow],
        warnings=warnings,
    )


def test_single_flow_mode_metadata():
    """Verify single-flow mode has correct metadata."""
    ir = _build_single_flow_ir()

    assert ir.ir_metadata.source_mode == InputMode.SINGLE_FLOW
    assert ir.ir_metadata.source_path == "/tmp/standalone-flow.xml"
    assert ir.ir_metadata.version == "1.0"


def test_project_metadata_empty():
    """Verify project metadata is empty in single-flow mode."""
    ir = _build_single_flow_ir()

    assert ir.project_metadata.name is None
    assert ir.project_metadata.group_id is None
    assert ir.project_metadata.artifact_id is None
    assert ir.project_metadata.version is None
    assert ir.project_metadata.description is None


def test_warnings_populated():
    """Verify warnings are populated for unresolvable references."""
    ir = _build_single_flow_ir()

    assert len(ir.warnings) == 3

    codes = [w.code for w in ir.warnings]
    assert codes.count("MISSING_CONNECTOR_CONFIG") == 2
    assert codes.count("UNRESOLVABLE_PROPERTY") == 1

    for w in ir.warnings:
        assert w.severity == Severity.WARNING


def test_flows_still_represented():
    """Verify flows are correctly represented despite missing context."""
    ir = _build_single_flow_ir()

    assert len(ir.flows) == 2

    # Main flow
    main_flow = ir.flows[0]
    assert main_flow.kind == FlowKind.FLOW
    assert main_flow.name == "items-flow"
    assert main_flow.trigger is not None
    assert main_flow.trigger.type == TriggerType.HTTP_LISTENER
    assert len(main_flow.steps) == 2

    # Sub-flow
    sub_flow = ir.flows[1]
    assert sub_flow.kind == FlowKind.SUB_FLOW
    assert sub_flow.name == "items-helper"
    assert sub_flow.trigger is None
    assert len(sub_flow.steps) == 1


def test_sub_flow_has_no_trigger():
    """Verify sub-flows do not have triggers."""
    ir = _build_single_flow_ir()
    sub_flow = ir.flows[1]
    assert sub_flow.trigger is None


def test_json_roundtrip():
    """Verify single-flow mode IR survives JSON roundtrip."""
    ir = _build_single_flow_ir()
    json_str = to_json(ir)
    restored = from_json(json_str)

    assert restored.ir_metadata.source_mode == InputMode.SINGLE_FLOW
    assert restored.project_metadata.name is None
    assert len(restored.warnings) == 3
    assert len(restored.flows) == 2
    assert restored.flows[0].kind == FlowKind.FLOW
    assert restored.flows[1].kind == FlowKind.SUB_FLOW


def test_json_contains_warnings():
    """Verify JSON output includes warning details."""
    ir = _build_single_flow_ir()
    json_str = to_json(ir)

    assert "MISSING_CONNECTOR_CONFIG" in json_str
    assert "UNRESOLVABLE_PROPERTY" in json_str
    assert "standalone-flow.xml" in json_str
