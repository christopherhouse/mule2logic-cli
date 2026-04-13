"""Tests: Scheduler trigger → foreach scope containing processors.

This represents a MuleSoft pattern for batch processing: a scheduled job
iterates over a collection and processes each item.
"""

from m2la_contracts.enums import InputMode

from m2la_ir import (
    FlowKind,
    ProcessorType,
    ScopeType,
    TriggerType,
    build_project_ir,
    from_json,
    make_db_operation,
    make_flow,
    make_foreach_scope,
    make_logger,
    make_scheduler_trigger,
    make_source_location,
    to_json,
)


def _build_scheduler_loop_ir():
    """Build an IR: scheduler trigger → foreach scope with db + logger."""
    trigger = make_scheduler_trigger(
        frequency="60000",
        time_unit="MILLISECONDS",
        source_location=make_source_location("src/main/mule/batch-flow.xml", line=4),
    )

    db_select = make_db_operation(
        operation="select",
        query="SELECT * FROM orders WHERE status = 'pending'",
        config_ref="Database_Config",
        source_location=make_source_location("src/main/mule/batch-flow.xml", line=10),
    )

    logger = make_logger(
        message="Processing order: #[payload.orderId]",
        level="INFO",
        source_location=make_source_location("src/main/mule/batch-flow.xml", line=18),
    )

    db_update = make_db_operation(
        operation="update",
        query="UPDATE orders SET status = 'processed' WHERE id = :id",
        config_ref="Database_Config",
        source_location=make_source_location("src/main/mule/batch-flow.xml", line=22),
    )

    foreach = make_foreach_scope(
        collection="#[payload]",
        steps=[logger, db_update],
        source_location=make_source_location("src/main/mule/batch-flow.xml", line=15),
    )

    flow = make_flow(
        name="batch-processing-flow",
        trigger=trigger,
        steps=[db_select, foreach],
        source_location=make_source_location("src/main/mule/batch-flow.xml", line=2),
    )

    return build_project_ir(
        source_path="/projects/batch-processor",
        project_name="batch-processor",
        group_id="com.example",
        artifact_id="batch-processor",
        version="2.0.0",
        flows=[flow],
    )


def test_scheduler_trigger():
    """Verify the scheduler trigger is correctly represented."""
    ir = _build_scheduler_loop_ir()
    flow = ir.flows[0]

    assert flow.trigger is not None
    assert flow.trigger.type == TriggerType.SCHEDULER
    assert flow.trigger.config["frequency"] == "60000"
    assert flow.trigger.config["timeUnit"] == "MILLISECONDS"


def test_foreach_scope_nesting():
    """Verify the foreach scope contains nested steps."""
    ir = _build_scheduler_loop_ir()
    steps = ir.flows[0].steps

    # Step 0 is db select, step 1 is foreach
    assert steps[0].step_type == "connector_operation"
    assert steps[1].step_type == "scope"
    assert steps[1].type == ScopeType.FOREACH
    assert steps[1].config["collection"] == "#[payload]"

    # foreach has 2 inner steps
    inner = steps[1].steps
    assert len(inner) == 2
    assert inner[0].step_type == "processor"
    assert inner[0].type == ProcessorType.LOGGER
    assert inner[1].step_type == "connector_operation"
    assert inner[1].operation == "update"


def test_processor_ordering():
    """Verify step ordering is preserved."""
    ir = _build_scheduler_loop_ir()
    flow = ir.flows[0]

    # Top-level: db_select → foreach
    assert len(flow.steps) == 2
    assert flow.steps[0].step_type == "connector_operation"
    assert flow.steps[1].step_type == "scope"

    # Inside foreach: logger → db_update
    inner = flow.steps[1].steps
    assert inner[0].step_type == "processor"
    assert inner[1].step_type == "connector_operation"


def test_flow_metadata():
    """Verify flow and project metadata."""
    ir = _build_scheduler_loop_ir()

    assert ir.ir_metadata.source_mode == InputMode.PROJECT
    assert ir.project_metadata.name == "batch-processor"
    assert ir.project_metadata.version == "2.0.0"
    assert ir.flows[0].kind == FlowKind.FLOW
    assert ir.flows[0].name == "batch-processing-flow"


def test_json_roundtrip():
    """Verify scheduler+loop IR survives JSON roundtrip."""
    ir = _build_scheduler_loop_ir()
    json_str = to_json(ir)
    restored = from_json(json_str)

    assert restored.flows[0].trigger.type == TriggerType.SCHEDULER
    assert restored.flows[0].steps[1].step_type == "scope"
    assert restored.flows[0].steps[1].type == ScopeType.FOREACH
    assert len(restored.flows[0].steps[1].steps) == 2
