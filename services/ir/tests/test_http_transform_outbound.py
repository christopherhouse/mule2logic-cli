"""Tests: HTTP listener → DataWeave transform → HTTP request outbound call.

This represents a common MuleSoft pattern where an API endpoint receives a
request, transforms the payload, and calls another HTTP service.
"""

from m2la_contracts.enums import InputMode

from m2la_ir import (
    ConnectorType,
    FlowKind,
    ProcessorType,
    TransformType,
    TriggerType,
    build_project_ir,
    from_json,
    make_dataweave_transform,
    make_flow,
    make_http_request,
    make_http_trigger,
    make_logger,
    make_source_location,
    to_json,
)


def _build_http_transform_outbound_ir():
    """Build an IR representing HTTP listener → transform → outbound HTTP call."""
    loc = make_source_location("src/main/mule/api-flow.xml", line=5)

    trigger = make_http_trigger(
        path="/api/orders",
        method="POST",
        config_ref="HTTP_Listener_config",
        source_location=loc,
    )

    transform = make_dataweave_transform(
        expression="%dw 2.0\noutput application/json\n---\n{\n  orderId: payload.id\n}",
        mime_type="application/json",
        source_location=make_source_location("src/main/mule/api-flow.xml", line=12),
    )

    logger = make_logger(
        message="Calling backend service",
        level="INFO",
        source_location=make_source_location("src/main/mule/api-flow.xml", line=20),
    )

    http_request = make_http_request(
        method="POST",
        url="/backend/orders",
        config_ref="HTTP_Request_config",
        source_location=make_source_location("src/main/mule/api-flow.xml", line=25),
    )

    flow = make_flow(
        name="api-main-flow",
        trigger=trigger,
        steps=[transform, logger, http_request],
        source_location=make_source_location("src/main/mule/api-flow.xml", line=3),
    )

    return build_project_ir(
        source_path="/projects/my-api",
        project_name="my-api",
        group_id="com.example",
        artifact_id="my-api",
        version="1.0.0",
        flows=[flow],
    )


def test_ir_structure():
    """Verify the IR tree has the expected structure."""
    ir = _build_http_transform_outbound_ir()

    assert ir.ir_metadata.source_mode == InputMode.PROJECT
    assert ir.ir_metadata.version == "1.0"
    assert ir.project_metadata.name == "my-api"
    assert len(ir.flows) == 1

    flow = ir.flows[0]
    assert flow.kind == FlowKind.FLOW
    assert flow.name == "api-main-flow"
    assert flow.trigger is not None
    assert flow.trigger.type == TriggerType.HTTP_LISTENER
    assert flow.trigger.config["path"] == "/api/orders"
    assert flow.trigger.config["method"] == "POST"
    assert len(flow.steps) == 3


def test_step_types():
    """Verify each step has the correct discriminated type."""
    ir = _build_http_transform_outbound_ir()
    steps = ir.flows[0].steps

    # Step 0: DataWeave transform
    assert steps[0].step_type == "transform"
    assert steps[0].type == TransformType.DATAWEAVE
    assert steps[0].mime_type == "application/json"
    assert "orderId" in steps[0].expression

    # Step 1: Logger processor
    assert steps[1].step_type == "processor"
    assert steps[1].type == ProcessorType.LOGGER

    # Step 2: HTTP request connector
    assert steps[2].step_type == "connector_operation"
    assert steps[2].connector_type == ConnectorType.HTTP_REQUEST
    assert steps[2].operation == "request"
    assert steps[2].config["url"] == "/backend/orders"


def test_source_locations():
    """Verify source locations are preserved."""
    ir = _build_http_transform_outbound_ir()
    flow = ir.flows[0]

    assert flow.source_location is not None
    assert flow.source_location.file == "src/main/mule/api-flow.xml"
    assert flow.source_location.line == 3

    assert flow.trigger.source_location.line == 5
    assert flow.steps[0].source_location.line == 12
    assert flow.steps[2].source_location.line == 25


def test_json_roundtrip():
    """Verify JSON serialization roundtrip is lossless."""
    ir = _build_http_transform_outbound_ir()
    json_str = to_json(ir)
    restored = from_json(json_str)

    assert restored.ir_metadata.source_mode == ir.ir_metadata.source_mode
    assert restored.project_metadata.name == ir.project_metadata.name
    assert len(restored.flows) == len(ir.flows)
    assert restored.flows[0].name == ir.flows[0].name
    assert restored.flows[0].trigger.type == ir.flows[0].trigger.type
    assert len(restored.flows[0].steps) == len(ir.flows[0].steps)

    # Verify step types survived roundtrip
    for orig, rest in zip(ir.flows[0].steps, restored.flows[0].steps, strict=True):
        assert orig.step_type == rest.step_type
