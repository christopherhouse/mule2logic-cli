"""Tests: Choice router with multiple routes + error handlers.

This represents a MuleSoft pattern where a choice router dispatches to
different processing paths based on conditions, with error handling.
"""

from m2la_ir import (
    ErrorHandlerType,
    FlowKind,
    ProcessorType,
    RouterType,
    build_project_ir,
    from_json,
    make_choice_router,
    make_error_handler,
    make_flow,
    make_http_request,
    make_http_trigger,
    make_logger,
    make_route,
    make_source_location,
    to_json,
)


def _build_choice_router_ir():
    """Build an IR with choice router + error handlers."""
    trigger = make_http_trigger(
        path="/api/process",
        method="POST",
        source_location=make_source_location("src/main/mule/router-flow.xml", line=4),
    )

    # Route 1: type == 'A'
    route_a = make_route(
        condition="#[payload.type == 'A']",
        steps=[
            make_logger(
                message="Processing type A",
                source_location=make_source_location("src/main/mule/router-flow.xml", line=12),
            ),
            make_http_request(
                method="POST",
                url="/service-a",
                source_location=make_source_location("src/main/mule/router-flow.xml", line=15),
            ),
        ],
    )

    # Route 2: type == 'B'
    route_b = make_route(
        condition="#[payload.type == 'B']",
        steps=[
            make_logger(
                message="Processing type B",
                source_location=make_source_location("src/main/mule/router-flow.xml", line=22),
            ),
        ],
    )

    # Default route
    default_route = make_route(
        steps=[
            make_logger(
                message="Unknown type — using default path",
                source_location=make_source_location("src/main/mule/router-flow.xml", line=30),
            ),
        ],
    )

    router = make_choice_router(
        routes=[route_a, route_b],
        default_route=default_route,
        source_location=make_source_location("src/main/mule/router-flow.xml", line=8),
    )

    # Error handlers
    propagate = make_error_handler(
        handler_type=ErrorHandlerType.ON_ERROR_PROPAGATE,
        error_type="MULE:CONNECTIVITY",
        steps=[
            make_logger(
                message="Connectivity error — propagating",
                level="ERROR",
                source_location=make_source_location("src/main/mule/router-flow.xml", line=40),
            ),
        ],
        source_location=make_source_location("src/main/mule/router-flow.xml", line=38),
    )

    continue_handler = make_error_handler(
        handler_type=ErrorHandlerType.ON_ERROR_CONTINUE,
        error_type="MULE:EXPRESSION",
        steps=[
            make_logger(
                message="Expression error — continuing with default",
                level="WARN",
                source_location=make_source_location("src/main/mule/router-flow.xml", line=48),
            ),
        ],
        source_location=make_source_location("src/main/mule/router-flow.xml", line=46),
    )

    flow = make_flow(
        name="router-flow",
        trigger=trigger,
        steps=[router],
        error_handlers=[propagate, continue_handler],
        source_location=make_source_location("src/main/mule/router-flow.xml", line=2),
    )

    return build_project_ir(
        source_path="/projects/router-app",
        project_name="router-app",
        flows=[flow],
    )


def test_choice_router_structure():
    """Verify choice router has correct routes."""
    ir = _build_choice_router_ir()
    flow = ir.flows[0]

    assert len(flow.steps) == 1
    router = flow.steps[0]

    assert router.step_type == "router"
    assert router.type == RouterType.CHOICE
    assert len(router.routes) == 2
    assert router.default_route is not None


def test_route_conditions():
    """Verify route conditions and contained steps."""
    ir = _build_choice_router_ir()
    router = ir.flows[0].steps[0]

    # Route A
    assert router.routes[0].condition == "#[payload.type == 'A']"
    assert len(router.routes[0].steps) == 2
    assert router.routes[0].steps[0].step_type == "processor"
    assert router.routes[0].steps[1].step_type == "connector_operation"

    # Route B
    assert router.routes[1].condition == "#[payload.type == 'B']"
    assert len(router.routes[1].steps) == 1

    # Default route (no condition)
    assert router.default_route.condition is None
    assert len(router.default_route.steps) == 1


def test_error_handlers():
    """Verify error handlers are correctly attached to the flow."""
    ir = _build_choice_router_ir()
    flow = ir.flows[0]

    assert len(flow.error_handlers) == 2

    # on-error-propagate
    eh0 = flow.error_handlers[0]
    assert eh0.type == ErrorHandlerType.ON_ERROR_PROPAGATE
    assert eh0.error_type == "MULE:CONNECTIVITY"
    assert len(eh0.steps) == 1
    assert eh0.steps[0].type == ProcessorType.LOGGER

    # on-error-continue
    eh1 = flow.error_handlers[1]
    assert eh1.type == ErrorHandlerType.ON_ERROR_CONTINUE
    assert eh1.error_type == "MULE:EXPRESSION"
    assert len(eh1.steps) == 1


def test_error_handler_source_locations():
    """Verify error handler source locations are preserved."""
    ir = _build_choice_router_ir()
    flow = ir.flows[0]

    assert flow.error_handlers[0].source_location.line == 38
    assert flow.error_handlers[1].source_location.line == 46


def test_json_roundtrip():
    """Verify choice router IR survives JSON roundtrip."""
    ir = _build_choice_router_ir()
    json_str = to_json(ir)
    restored = from_json(json_str)

    router = restored.flows[0].steps[0]
    assert router.step_type == "router"
    assert router.type == RouterType.CHOICE
    assert len(router.routes) == 2
    assert router.default_route is not None

    assert len(restored.flows[0].error_handlers) == 2
    assert restored.flows[0].error_handlers[0].type == ErrorHandlerType.ON_ERROR_PROPAGATE


def test_flow_kind():
    """Verify the flow is of the correct kind."""
    ir = _build_choice_router_ir()
    assert ir.flows[0].kind == FlowKind.FLOW
