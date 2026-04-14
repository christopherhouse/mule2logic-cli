"""Comprehensive tests for all MVP construct transformations (PR-010).

Tests cover:
- Choice router → If / Switch with nested actions
- Scatter-gather → Parallel branches
- Foreach → Foreach with nested actions
- Try scope → Scope with nested actions
- Until-successful → Until loop
- Async scope → sequential Scope
- Parallel foreach → Foreach with concurrency
- Flow-ref → Scope with inlined sub-flow
- Error handlers → Scope + runAfter failure conditions
- DataWeave expression conversion
- File/FTP/SFTP/VM/Email connectors
- SQL/Database operations
- Messaging (MQ) → ServiceBus
- Raise-error → Terminate action
"""

from __future__ import annotations

from typing import Any

from m2la_ir.builders import (
    make_choice_router,
    make_dataweave_transform,
    make_db_operation,
    make_error_handler,
    make_flow,
    make_foreach_scope,
    make_http_request,
    make_http_trigger,
    make_logger,
    make_processor,
    make_route,
    make_set_variable,
    make_try_scope,
)
from m2la_ir.enums import (
    ConnectorType,
    ErrorHandlerType,
    FlowKind,
    ProcessorType,
    RouterType,
    ScopeType,
)
from m2la_ir.models import (
    ConnectorOperation,
    Route,
    Router,
    Scope,
)

from m2la_transform.workflow_generator import (
    convert_dataweave_expression,
    generate_workflow,
)


def _actions(wf: dict[str, Any]) -> dict[str, Any]:
    return wf["definition"]["actions"]


def _triggers(wf: dict[str, Any]) -> dict[str, Any]:
    return wf["definition"]["triggers"]


# ── DataWeave expression conversion ──────────────────────────────────────────


class TestDataWeaveConversion:
    """Tests for convert_dataweave_expression."""

    def test_simple_payload(self) -> None:
        result, converted = convert_dataweave_expression("#[payload]")
        assert converted is True
        assert result == "@triggerBody()"

    def test_payload_property(self) -> None:
        result, converted = convert_dataweave_expression("#[payload.orderId]")
        assert converted is True
        assert result == "@triggerBody()?['orderId']"

    def test_variable_reference(self) -> None:
        result, converted = convert_dataweave_expression("#[vars.myVar]")
        assert converted is True
        assert result == "@variables('myVar')"

    def test_attribute_reference(self) -> None:
        result, converted = convert_dataweave_expression("#[attributes.contentType]")
        assert converted is True
        assert result == "@triggerOutputs()?['headers']['contentType']"

    def test_complex_dw_not_converted(self) -> None:
        complex_dw = """%dw 2.0
output application/json
---
{
    data: payload map (item) -> { id: item.id }
}"""
        result, converted = convert_dataweave_expression(complex_dw)
        assert converted is False
        assert result == complex_dw

    def test_bare_payload_without_wrapper(self) -> None:
        result, converted = convert_dataweave_expression("payload")
        assert converted is True
        assert result == "@triggerBody()"

    def test_empty_string(self) -> None:
        result, converted = convert_dataweave_expression("")
        assert converted is False


# ── Choice router ─────────────────────────────────────────────────────────────


class TestChoiceRouter:
    """Tests for choice router → If / Switch action."""

    def test_single_condition_maps_to_if(self) -> None:
        """Single when/otherwise → If action with true/false branches."""
        router = make_choice_router(
            routes=[
                make_route(
                    condition="#[payload]",
                    steps=[make_logger(message="condition met")],
                ),
            ],
            default_route=make_route(
                steps=[make_logger(message="default")],
            ),
        )
        flow = make_flow(
            name="choice-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[router],
        )
        wf, gaps = generate_workflow(flow)

        actions = _actions(wf)
        assert len(actions) == 1
        choice_action = list(actions.values())[0]
        assert choice_action["type"] == "If"
        assert "actions" in choice_action
        assert "else" in choice_action
        assert choice_action["else"]["actions"]  # default route has actions

    def test_if_has_nested_true_actions(self) -> None:
        """If action nests the 'when' route's steps."""
        router = make_choice_router(
            routes=[
                make_route(
                    condition="#[payload]",
                    steps=[
                        make_set_variable(variable_name="x", value="1"),
                        make_logger(message="after set"),
                    ],
                ),
            ],
        )
        flow = make_flow(
            name="if-nested",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[router],
        )
        wf, _ = generate_workflow(flow)

        if_action = list(_actions(wf).values())[0]
        assert len(if_action["actions"]) == 2

    def test_multiple_conditions_maps_to_switch(self) -> None:
        """Multiple when branches → Switch action with cases."""
        router = make_choice_router(
            routes=[
                make_route(condition="case_a", steps=[make_logger(message="A")]),
                make_route(condition="case_b", steps=[make_logger(message="B")]),
            ],
            default_route=make_route(steps=[make_logger(message="default")]),
        )
        flow = make_flow(
            name="switch-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[router],
        )
        wf, gaps = generate_workflow(flow)

        switch_action = list(_actions(wf).values())[0]
        assert switch_action["type"] == "Switch"
        assert "cases" in switch_action
        assert len(switch_action["cases"]) == 2
        assert "default" in switch_action

    def test_choice_emits_partial_support_gap(self) -> None:
        """Choice router always emits at least one gap for expression review."""
        router = make_choice_router(
            routes=[
                make_route(condition="complex expression", steps=[]),
                make_route(condition="another", steps=[]),
            ],
        )
        flow = make_flow(
            name="choice-gap",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[router],
        )
        _, gaps = generate_workflow(flow)

        assert any("router:choice" in g.construct_name for g in gaps)


# ── Scatter-gather ────────────────────────────────────────────────────────────


class TestScatterGather:
    """Tests for scatter-gather → parallel branch pattern."""

    def test_scatter_gather_creates_parallel_branches(self) -> None:
        """Each route becomes a branch Scope; a join action follows."""
        router = Router(
            type=RouterType.SCATTER_GATHER,
            routes=[
                Route(steps=[make_logger(message="branch 1")]),
                Route(steps=[make_logger(message="branch 2")]),
            ],
        )
        flow = make_flow(
            name="scatter-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[router],
        )
        wf, gaps = generate_workflow(flow)

        outer_scope = list(_actions(wf).values())[0]
        assert outer_scope["type"] == "Scope"
        inner = outer_scope["actions"]
        assert "Branch_0" in inner
        assert "Branch_1" in inner
        assert "Join_Branches" in inner

    def test_scatter_gather_branches_have_nested_actions(self) -> None:
        router = Router(
            type=RouterType.SCATTER_GATHER,
            routes=[
                Route(steps=[make_set_variable(variable_name="a", value="1")]),
                Route(
                    steps=[
                        make_set_variable(variable_name="b", value="2"),
                        make_logger(message="done"),
                    ]
                ),
            ],
        )
        flow = make_flow(
            name="sg-nested",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[router],
        )
        wf, _ = generate_workflow(flow)

        outer = list(_actions(wf).values())[0]
        branch_1 = outer["actions"]["Branch_1"]
        assert len(branch_1["actions"]) == 2

    def test_scatter_gather_emits_gap(self) -> None:
        router = Router(
            type=RouterType.SCATTER_GATHER,
            routes=[Route(steps=[])],
        )
        flow = make_flow(
            name="sg-gap",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[router],
        )
        _, gaps = generate_workflow(flow)
        assert any("scatter_gather" in g.construct_name for g in gaps)


# ── Foreach ───────────────────────────────────────────────────────────────────


class TestForeach:
    """Tests for foreach → Foreach with nested actions."""

    def test_foreach_has_nested_actions(self) -> None:
        scope = make_foreach_scope(
            collection="#[payload]",
            steps=[
                make_set_variable(variable_name="item", value="#[payload]"),
                make_logger(message="processing"),
            ],
        )
        flow = make_flow(
            name="foreach-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[scope],
        )
        wf, _ = generate_workflow(flow)

        foreach = list(_actions(wf).values())[0]
        assert foreach["type"] == "Foreach"
        assert len(foreach["actions"]) == 2

    def test_foreach_collection_expression(self) -> None:
        scope = make_foreach_scope(collection="#[payload]")
        flow = make_flow(
            name="foreach-expr",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[scope],
        )
        wf, _ = generate_workflow(flow)

        foreach = list(_actions(wf).values())[0]
        assert foreach["foreach"] == "@triggerBody()"  # DW conversion


# ── Parallel Foreach ──────────────────────────────────────────────────────────


class TestParallelForeach:
    """Tests for parallel-foreach → Foreach with concurrency."""

    def test_parallel_foreach_has_concurrency(self) -> None:
        scope = Scope(
            type=ScopeType.PARALLEL_FOREACH,
            steps=[make_logger(message="parallel item")],
            config={"collection": "#[payload]", "max_concurrency": 10},
        )
        flow = make_flow(
            name="parallel-foreach",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[scope],
        )
        wf, _ = generate_workflow(flow)

        foreach = list(_actions(wf).values())[0]
        assert foreach["type"] == "Foreach"
        assert foreach["runtimeConfiguration"]["concurrency"]["repetitions"] == 10


# ── Try Scope ─────────────────────────────────────────────────────────────────


class TestTryScope:
    """Tests for try scope → Scope with nested actions."""

    def test_try_scope_has_nested_actions(self) -> None:
        scope = make_try_scope(
            steps=[
                make_http_request(method="GET", url="https://api.example.com"),
                make_logger(message="success"),
            ],
        )
        flow = make_flow(
            name="try-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[scope],
        )
        wf, _ = generate_workflow(flow)

        scope_action = list(_actions(wf).values())[0]
        assert scope_action["type"] == "Scope"
        assert len(scope_action["actions"]) == 2


# ── Until-Successful ─────────────────────────────────────────────────────────


class TestUntilSuccessful:
    """Tests for until-successful → Until loop."""

    def test_until_successful_maps_to_until(self) -> None:
        scope = Scope(
            type=ScopeType.UNTIL_SUCCESSFUL,
            steps=[make_http_request(method="GET", url="https://api.example.com/check")],
            config={"maxRetries": 3},
        )
        flow = make_flow(
            name="retry-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[scope],
        )
        wf, gaps = generate_workflow(flow)

        until = list(_actions(wf).values())[0]
        assert until["type"] == "Until"
        assert until["limit"]["count"] == 3
        assert len(until["actions"]) == 1
        assert any("until_successful" in g.construct_name for g in gaps)


# ── Async Scope ──────────────────────────────────────────────────────────────


class TestAsyncScope:
    """Tests for async scope → sequential Scope with warning."""

    def test_async_scope_maps_to_scope(self) -> None:
        scope = Scope(
            type=ScopeType.ASYNC_SCOPE,
            steps=[make_logger(message="async work")],
        )
        flow = make_flow(
            name="async-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[scope],
        )
        wf, gaps = generate_workflow(flow)

        scope_action = list(_actions(wf).values())[0]
        assert scope_action["type"] == "Scope"
        assert "fire-and-forget" in scope_action.get("description", "")
        assert any("async_scope" in g.construct_name for g in gaps)


# ── Flow-ref (sub-flow inlining) ─────────────────────────────────────────────


class TestFlowRef:
    """Tests for flow-ref resolution and sub-flow inlining."""

    def test_flow_ref_inlines_subflow(self) -> None:
        """When sub-flow is available, its steps are inlined into a Scope."""
        sub_flow = make_flow(
            name="shared-logic",
            kind=FlowKind.SUB_FLOW,
            steps=[
                make_set_variable(variable_name="status", value="processed"),
                make_logger(message="sub-flow done"),
            ],
        )
        main_flow = make_flow(
            name="main-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[
                make_processor(ProcessorType.FLOW_REF, config={"flow_name": "shared-logic"}),
            ],
        )

        wf, gaps = generate_workflow(main_flow, sub_flows={"shared-logic": sub_flow})

        actions = _actions(wf)
        scope_action = list(actions.values())[0]
        assert scope_action["type"] == "Scope"
        assert len(scope_action["actions"]) == 2
        assert "Inlined sub-flow" in scope_action.get("description", "")
        # Should NOT produce a gap when resolved
        assert not any(g.construct_name == "flow_ref" for g in gaps)

    def test_flow_ref_unresolved_emits_gap(self) -> None:
        """When sub-flow is not found, emits a migration gap."""
        flow = make_flow(
            name="ref-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[
                make_processor(ProcessorType.FLOW_REF, config={"flow_name": "missing-flow"}),
            ],
        )
        wf, gaps = generate_workflow(flow)

        scope_action = list(_actions(wf).values())[0]
        assert scope_action["type"] == "Scope"
        assert scope_action["actions"] == {}
        assert "MIGRATION GAP" in scope_action.get("description", "")
        assert any(g.construct_name == "flow_ref" for g in gaps)


# ── Error handlers ────────────────────────────────────────────────────────────


class TestErrorHandlers:
    """Tests for error handler → Scope + runAfter failure conditions."""

    def test_error_handler_creates_scope_with_failure_run_after(self) -> None:
        """on-error-propagate → Scope with runAfter: Failed/TimedOut."""
        flow = make_flow(
            name="error-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[make_http_request(method="GET", url="https://api.example.com")],
            error_handlers=[
                make_error_handler(
                    handler_type=ErrorHandlerType.ON_ERROR_PROPAGATE,
                    error_type="HTTP:CONNECTIVITY",
                    steps=[make_logger(message="error occurred")],
                ),
            ],
        )
        wf, _ = generate_workflow(flow)

        actions = _actions(wf)
        # Should have main step + error handler
        assert len(actions) == 2

        error_action = list(actions.values())[1]
        assert error_action["type"] == "Scope"
        run_after = error_action["runAfter"]
        assert run_after
        statuses = list(run_after.values())[0]
        assert "Failed" in statuses
        assert "TimedOut" in statuses

    def test_on_error_continue_has_description(self) -> None:
        """on-error-continue → Scope with 'continues execution' description."""
        flow = make_flow(
            name="continue-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[make_logger(message="main")],
            error_handlers=[
                make_error_handler(
                    handler_type=ErrorHandlerType.ON_ERROR_CONTINUE,
                    error_type="ANY",
                    steps=[make_logger(message="handled")],
                ),
            ],
        )
        wf, _ = generate_workflow(flow)

        error_action = list(_actions(wf).values())[1]
        assert "continues execution" in error_action.get("description", "")

    def test_multiple_error_handlers(self) -> None:
        """Multiple error handlers create multiple Scope actions."""
        flow = make_flow(
            name="multi-error",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[make_logger(message="step")],
            error_handlers=[
                make_error_handler(
                    handler_type=ErrorHandlerType.ON_ERROR_PROPAGATE,
                    error_type="HTTP:CONNECTIVITY",
                    steps=[make_logger(message="handler 1")],
                ),
                make_error_handler(
                    handler_type=ErrorHandlerType.ON_ERROR_CONTINUE,
                    error_type="ANY",
                    steps=[make_logger(message="handler 2")],
                ),
            ],
        )
        wf, _ = generate_workflow(flow)

        actions = _actions(wf)
        # 1 main step + 2 error handlers
        assert len(actions) == 3


# ── DataWeave transform step ─────────────────────────────────────────────────


class TestDataWeaveTransform:
    """Tests for DataWeave transform steps → Compose actions."""

    def test_simple_dw_expression_converted(self) -> None:
        """Simple #[payload] DataWeave → @triggerBody()."""
        transform = make_dataweave_transform(expression="#[payload]")
        flow = make_flow(
            name="dw-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[transform],
        )
        wf, gaps = generate_workflow(flow)

        action = list(_actions(wf).values())[0]
        assert action["type"] == "Compose"
        assert action["inputs"]["expression"] == "@triggerBody()"
        # Simple expression → no gap
        dw_gaps = [g for g in gaps if "dataweave" in g.construct_name]
        assert not dw_gaps

    def test_complex_dw_expression_emits_gap(self) -> None:
        """Complex DataWeave expression → gap emitted."""
        complex_expr = "%dw 2.0\noutput application/json\n---\npayload map (item) -> item"
        transform = make_dataweave_transform(expression=complex_expr)
        flow = make_flow(
            name="complex-dw",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[transform],
        )
        _, gaps = generate_workflow(flow)

        dw_gaps = [g for g in gaps if "dataweave" in g.construct_name]
        assert dw_gaps


# ── Database operations ──────────────────────────────────────────────────────


class TestDatabaseOperations:
    """Tests for DB connector → SQL ApiConnection."""

    def test_db_select_maps_to_query(self) -> None:
        db_op = make_db_operation(operation="select", query="SELECT * FROM orders")
        flow = make_flow(
            name="db-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[db_op],
        )
        wf, gaps = generate_workflow(flow)

        action = list(_actions(wf).values())[0]
        assert action["type"] == "ApiConnection"
        assert "sql_connection" in str(action["inputs"]["host"])
        assert action["inputs"]["body"]["query"] == "SELECT * FROM orders"
        assert not gaps  # DB is fully supported

    def test_db_insert_maps_to_execute(self) -> None:
        db_op = make_db_operation(operation="insert", query="INSERT INTO orders VALUES(1)")
        flow = make_flow(
            name="db-insert",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[db_op],
        )
        wf, _ = generate_workflow(flow)

        action = list(_actions(wf).values())[0]
        assert action["type"] == "ApiConnection"
        assert "execute" in action["inputs"]["path"]


# ── Messaging (MQ → Service Bus) ─────────────────────────────────────────────


class TestMessaging:
    """Tests for MQ connector → Service Bus."""

    def test_mq_maps_to_servicebus(self) -> None:
        mq_op = ConnectorOperation(
            connector_type=ConnectorType.MQ,
            operation="publish",
            config={"destination": "orders-topic", "body": {"key": "value"}},
        )
        flow = make_flow(
            name="mq-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[mq_op],
        )
        wf, gaps = generate_workflow(flow)

        action = list(_actions(wf).values())[0]
        assert action["type"] == "ApiConnection"
        assert "servicebus_connection" in str(action["inputs"]["host"])
        assert "orders-topic" in action["inputs"]["path"]
        assert not gaps


# ── Raise error ──────────────────────────────────────────────────────────────


class TestRaiseError:
    """Tests for raise-error → Terminate action."""

    def test_raise_error_maps_to_terminate(self) -> None:
        step = make_processor(
            ProcessorType.RAISE_ERROR,
            config={"type": "APP:VALIDATION_ERROR", "description": "Invalid input"},
        )
        flow = make_flow(
            name="raise-error-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[step],
        )
        wf, _ = generate_workflow(flow)

        action = list(_actions(wf).values())[0]
        assert action["type"] == "Terminate"
        assert action["inputs"]["runStatus"] == "Failed"
        assert action["inputs"]["runError"]["code"] == "APP:VALIDATION_ERROR"


# ── Nested constructs ────────────────────────────────────────────────────────


class TestNestedConstructs:
    """Tests for deeply nested construct conversion."""

    def test_foreach_inside_choice(self) -> None:
        """Foreach nested inside a choice router branch."""
        foreach = make_foreach_scope(
            collection="#[payload]",
            steps=[make_logger(message="in loop")],
        )
        router = make_choice_router(
            routes=[make_route(condition="#[payload]", steps=[foreach])],
        )
        flow = make_flow(
            name="nested-flow",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[router],
        )
        wf, _ = generate_workflow(flow)

        if_action = list(_actions(wf).values())[0]
        assert if_action["type"] == "If"
        nested = if_action["actions"]
        assert len(nested) == 1
        foreach_action = list(nested.values())[0]
        assert foreach_action["type"] == "Foreach"
        assert len(foreach_action["actions"]) == 1

    def test_try_scope_with_error_handler_on_flow(self) -> None:
        """Try scope + flow-level error handler produces correct structure."""
        flow = make_flow(
            name="try-error",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[
                make_try_scope(steps=[make_http_request(method="GET", url="https://api.test")]),
            ],
            error_handlers=[
                make_error_handler(
                    handler_type=ErrorHandlerType.ON_ERROR_PROPAGATE,
                    steps=[make_logger(message="flow-level error")],
                ),
            ],
        )
        wf, _ = generate_workflow(flow)

        actions = _actions(wf)
        # try scope + error handler scope
        assert len(actions) == 2


# ── RunAfter chaining with mixed constructs ──────────────────────────────────


class TestRunAfterChaining:
    """Tests that runAfter chains correctly through mixed construct types."""

    def test_chaining_across_different_step_types(self) -> None:
        """Steps of different types chain correctly via runAfter."""
        flow = make_flow(
            name="mixed-chain",
            kind=FlowKind.FLOW,
            trigger=make_http_trigger(),
            steps=[
                make_set_variable(variable_name="x", value="1"),
                make_logger(message="log"),
                make_http_request(method="GET", url="https://api.test"),
                make_dataweave_transform(expression="#[payload]"),
            ],
        )
        wf, _ = generate_workflow(flow)

        actions = _actions(wf)
        assert len(actions) == 4

        action_names = list(actions.keys())
        action_list = list(actions.values())

        # First has empty runAfter
        assert action_list[0]["runAfter"] == {}

        # Each subsequent references the previous
        for i in range(1, len(action_list)):
            assert action_names[i - 1] in action_list[i]["runAfter"]
