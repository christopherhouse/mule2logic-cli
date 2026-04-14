"""Tests for the per-flow workflow generator (workflow_generator.py)."""

from __future__ import annotations

from typing import Any

import pytest
from m2la_ir.builders import (
    make_flow,
    make_http_request,
    make_http_trigger,
    make_logger,
)
from m2la_ir.enums import FlowKind, TriggerType
from m2la_ir.models import Flow, Trigger

from m2la_transform.workflow_generator import WORKFLOW_SCHEMA, generate_workflow

# ── helpers ───────────────────────────────────────────────────────────────────


def _triggers(wf: dict[str, Any]) -> dict[str, Any]:
    return wf["definition"]["triggers"]


def _actions(wf: dict[str, Any]) -> dict[str, Any]:
    return wf["definition"]["actions"]


# ── trigger mapping ───────────────────────────────────────────────────────────


def test_http_trigger_maps_to_request(simple_http_flow: Flow) -> None:
    """HTTP_LISTENER trigger → 'Request' trigger type."""
    wf, gaps = generate_workflow(simple_http_flow)

    triggers = _triggers(wf)
    assert triggers, "Expected at least one trigger"
    trigger_def = next(iter(triggers.values()))
    assert trigger_def["type"] == "Request"
    assert trigger_def["kind"] == "Http"
    assert not gaps or all(g.construct_name != "trigger:http_listener" for g in gaps)


def test_scheduler_trigger_maps_to_recurrence(simple_scheduler_flow: Flow) -> None:
    """SCHEDULER trigger → 'Recurrence' trigger type with frequency/interval."""
    wf, gaps = generate_workflow(simple_scheduler_flow)

    triggers = _triggers(wf)
    assert triggers
    trigger_def = next(iter(triggers.values()))
    assert trigger_def["type"] == "Recurrence"
    assert "recurrence" in trigger_def
    recurrence = trigger_def["recurrence"]
    assert "frequency" in recurrence
    assert "interval" in recurrence
    assert isinstance(recurrence["interval"], int)


def test_unknown_trigger_emits_gap() -> None:
    """An unsupported trigger type emits a MigrationGap."""
    flow = make_flow(
        name="vm-listener-flow",
        kind=FlowKind.FLOW,
        trigger=Trigger(type=TriggerType.VM_LISTENER, config={}),
        steps=[],
    )
    wf, gaps = generate_workflow(flow)

    gap_names = [g.construct_name for g in gaps]
    assert any("trigger:" in name for name in gap_names), f"Expected a trigger gap; got: {gap_names}"
    # Should still produce a valid (placeholder) trigger
    assert _triggers(wf)


def test_flow_without_trigger_produces_empty_triggers() -> None:
    """A sub-flow with no trigger produces an empty triggers dict."""
    from m2la_ir.enums import FlowKind

    flow = make_flow(name="sub-flow", kind=FlowKind.SUB_FLOW, steps=[])
    wf, _ = generate_workflow(flow)

    assert _triggers(wf) == {}


# ── action mapping ────────────────────────────────────────────────────────────


def test_logger_maps_to_compose(simple_http_flow: Flow) -> None:
    """Logger processor step → Compose action."""
    wf, _ = generate_workflow(simple_http_flow)

    actions = _actions(wf)
    compose_actions = [v for v in actions.values() if v["type"] == "Compose"]
    assert compose_actions, "Expected at least one Compose action for logger"


def test_variable_set_maps_to_initialize_variable(simple_http_flow: Flow) -> None:
    """VariableOperation(set) → InitializeVariable action."""
    wf, _ = generate_workflow(simple_http_flow)

    actions = _actions(wf)
    init_var_actions = [v for v in actions.values() if v["type"] == "InitializeVariable"]
    assert init_var_actions, "Expected at least one InitializeVariable action"

    # Verify structure
    iv = init_var_actions[0]
    assert "variables" in iv["inputs"]
    variables = iv["inputs"]["variables"]
    assert variables
    assert "name" in variables[0]
    assert "type" in variables[0]
    assert "value" in variables[0]


def test_set_payload_maps_to_compose(simple_scheduler_flow: Flow) -> None:
    """SET_PAYLOAD processor → Compose action with payload input."""
    wf, _ = generate_workflow(simple_scheduler_flow)

    actions = _actions(wf)
    payload_actions = [v for v in actions.values() if v["type"] == "Compose" and "payload" in v.get("inputs", {})]
    assert payload_actions, "Expected a Compose action with 'payload' input for SET_PAYLOAD"


def test_http_connector_maps_to_http_action() -> None:
    """HTTP_REQUEST connector → Http action type."""
    flow = make_flow(
        name="http-flow",
        kind=FlowKind.FLOW,
        trigger=make_http_trigger(),
        steps=[make_http_request(method="POST", url="https://api.example.com/data")],
    )
    wf, gaps = generate_workflow(flow)

    actions = _actions(wf)
    http_actions = [v for v in actions.values() if v["type"] == "Http"]
    assert http_actions, "Expected an Http action"
    assert http_actions[0]["inputs"]["method"] == "POST"
    assert http_actions[0]["inputs"]["uri"] == "https://api.example.com/data"
    # No gap for supported connector
    connector_gaps = [g for g in gaps if "connector:" in g.construct_name]
    assert not connector_gaps


# ── runAfter chaining ─────────────────────────────────────────────────────────


def test_runafter_chains_actions(simple_http_flow: Flow) -> None:
    """Actions are chained via runAfter: first has empty {}, rest reference previous."""
    wf, _ = generate_workflow(simple_http_flow)

    actions = _actions(wf)
    assert len(actions) >= 2, "Need at least 2 steps to test chaining"

    action_list = list(actions.values())

    # First action has no predecessors
    first = action_list[0]
    assert first["runAfter"] == {}, f"First action runAfter must be empty, got: {first['runAfter']}"

    # Each subsequent action references the previous by name
    action_names = list(actions.keys())
    for i in range(1, len(action_list)):
        current = action_list[i]
        expected_predecessor = action_names[i - 1]
        assert expected_predecessor in current["runAfter"], (
            f"Action[{i}] '{action_names[i]}' should run after '{expected_predecessor}'"
        )
        assert current["runAfter"][expected_predecessor] == ["Succeeded"]


def test_single_step_has_empty_runafter() -> None:
    """A flow with exactly one step has that step with empty runAfter."""
    flow = make_flow(
        name="one-step",
        kind=FlowKind.FLOW,
        trigger=make_http_trigger(),
        steps=[make_logger(message="only step")],
    )
    wf, _ = generate_workflow(flow)

    actions = _actions(wf)
    assert len(actions) == 1
    assert list(actions.values())[0]["runAfter"] == {}


# ── schema validation ─────────────────────────────────────────────────────────


def test_workflow_has_required_schema(simple_http_flow: Flow) -> None:
    """Generated workflow dict has the required $schema and contentVersion."""
    wf, _ = generate_workflow(simple_http_flow)

    definition = wf["definition"]
    assert definition["$schema"] == WORKFLOW_SCHEMA
    assert definition["contentVersion"] == "1.0.0.0"
    assert "triggers" in definition
    assert "actions" in definition
    assert "outputs" in definition


def test_workflow_kind_is_stateful(simple_http_flow: Flow) -> None:
    """Workflow kind defaults to 'Stateful'."""
    wf, _ = generate_workflow(simple_http_flow)
    assert wf["kind"] == "Stateful"


# ── gap emission ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "connector_type",
    ["email", "vm", "file", "generic"],
)
def test_unsupported_connector_emits_gap(connector_type: str) -> None:
    """Unsupported connector types emit a MigrationGap."""
    from m2la_ir.enums import ConnectorType
    from m2la_ir.models import ConnectorOperation

    ct = ConnectorType(connector_type)
    step = ConnectorOperation(connector_type=ct, operation="send", config={})
    flow = make_flow(
        name="unsupported-connector-flow",
        kind=FlowKind.FLOW,
        trigger=make_http_trigger(),
        steps=[step],
    )
    _, gaps = generate_workflow(flow)

    assert gaps, f"Expected at least one gap for unsupported connector '{connector_type}'"
    gap_names = [g.construct_name for g in gaps]
    assert any("connector:" in n for n in gap_names)


def test_flow_ref_emits_gap() -> None:
    """FLOW_REF processor emits a MigrationGap."""
    from m2la_ir.builders import make_processor
    from m2la_ir.enums import ProcessorType

    flow = make_flow(
        name="flow-ref-flow",
        kind=FlowKind.FLOW,
        trigger=make_http_trigger(),
        steps=[make_processor(ProcessorType.FLOW_REF, config={"flow_name": "other-flow"})],
    )
    _, gaps = generate_workflow(flow)

    assert gaps
    assert any(g.construct_name == "flow_ref" for g in gaps)


def test_remove_variable_emits_gap() -> None:
    """remove-variable operation emits a MigrationGap."""
    from m2la_ir.builders import make_remove_variable

    flow = make_flow(
        name="remove-var-flow",
        kind=FlowKind.FLOW,
        trigger=make_http_trigger(),
        steps=[make_remove_variable(variable_name="tempVar")],
    )
    _, gaps = generate_workflow(flow)

    assert gaps
    assert any("remove_variable" in g.construct_name for g in gaps)
