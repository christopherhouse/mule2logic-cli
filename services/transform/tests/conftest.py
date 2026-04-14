"""Shared fixtures for m2la_transform tests."""

from __future__ import annotations

import pytest
from m2la_ir.builders import (
    build_project_ir,
    build_single_flow_ir,
    make_flow,
    make_http_trigger,
    make_logger,
    make_scheduler_trigger,
    make_set_variable,
)
from m2la_ir.enums import FlowKind, ProcessorType
from m2la_ir.models import Flow, MuleIR


@pytest.fixture
def simple_http_flow() -> Flow:
    """A flow with HTTP listener trigger + logger + set-variable step."""
    return make_flow(
        name="get orders flow",
        kind=FlowKind.FLOW,
        trigger=make_http_trigger(path="/orders", method="GET"),
        steps=[
            make_logger(message="Processing request", level="INFO"),
            make_set_variable(variable_name="correlationId", value="#[correlationId]"),
        ],
    )


@pytest.fixture
def simple_scheduler_flow() -> Flow:
    """A flow with scheduler trigger + set-payload processor."""
    from m2la_ir.builders import make_processor

    return make_flow(
        name="sync job flow",
        kind=FlowKind.FLOW,
        trigger=make_scheduler_trigger(frequency="5", time_unit="MINUTES"),
        steps=[
            make_processor(ProcessorType.SET_PAYLOAD, config={"value": "#[{'status': 'ok'}]"}),
        ],
    )


@pytest.fixture
def project_ir(simple_http_flow: Flow, simple_scheduler_flow: Flow) -> MuleIR:
    """Full project-mode IR with two flows."""
    return build_project_ir(
        source_path="/projects/my-api",
        project_name="my-api",
        artifact_id="my-api",
        version="1.0.0",
        flows=[simple_http_flow, simple_scheduler_flow],
    )


@pytest.fixture
def single_flow_ir(simple_http_flow: Flow) -> MuleIR:
    """Single-flow-mode IR with one HTTP listener flow."""
    return build_single_flow_ir(
        source_path="/flows/get-orders.xml",
        flows=[simple_http_flow],
    )
