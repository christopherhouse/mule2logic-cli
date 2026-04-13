"""Tests: Model validation, required fields, defaults, and enum values."""

import pytest
from m2la_contracts.enums import InputMode
from pydantic import ValidationError

from m2la_ir import IR_VERSION
from m2la_ir.enums import (
    ConnectorType,
    ErrorHandlerType,
    FlowKind,
    ProcessorType,
    RouterType,
    ScopeType,
    TransformType,
    TriggerType,
)
from m2la_ir.models import (
    ConnectorOperation,
    ErrorHandler,
    Flow,
    IRMetadata,
    MuleIR,
    Processor,
    ProjectMetadata,
    Route,
    Router,
    Scope,
    SourceLocation,
    Transform,
    Trigger,
    VariableOperation,
)


class TestIRMetadata:
    def test_defaults(self):
        meta = IRMetadata(source_mode=InputMode.PROJECT, source_path="/test")
        assert meta.version == IR_VERSION
        assert meta.generated_at is not None

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            IRMetadata()  # type: ignore[call-arg]

    def test_custom_version(self):
        meta = IRMetadata(source_mode=InputMode.PROJECT, source_path="/test", version="2.0")
        assert meta.version == "2.0"


class TestProjectMetadata:
    def test_all_optional(self):
        meta = ProjectMetadata()
        assert meta.name is None
        assert meta.group_id is None
        assert meta.artifact_id is None
        assert meta.version is None
        assert meta.description is None

    def test_full_metadata(self):
        meta = ProjectMetadata(
            name="my-app",
            group_id="com.example",
            artifact_id="my-app",
            version="1.0.0",
            description="Test app",
        )
        assert meta.name == "my-app"
        assert meta.group_id == "com.example"


class TestSourceLocation:
    def test_file_only(self):
        loc = SourceLocation(file="test.xml")
        assert loc.file == "test.xml"
        assert loc.line is None
        assert loc.column is None

    def test_full_location(self):
        loc = SourceLocation(file="test.xml", line=10, column=5)
        assert loc.line == 10
        assert loc.column == 5

    def test_line_validation(self):
        with pytest.raises(ValidationError):
            SourceLocation(file="test.xml", line=0)

    def test_column_validation(self):
        with pytest.raises(ValidationError):
            SourceLocation(file="test.xml", column=0)

    def test_requires_file(self):
        with pytest.raises(ValidationError):
            SourceLocation()  # type: ignore[call-arg]


class TestTrigger:
    def test_minimal(self):
        t = Trigger(type=TriggerType.HTTP_LISTENER)
        assert t.type == TriggerType.HTTP_LISTENER
        assert t.config == {}
        assert t.source_location is None

    def test_with_config(self):
        t = Trigger(type=TriggerType.SCHEDULER, config={"frequency": "1000"})
        assert t.config["frequency"] == "1000"


class TestProcessor:
    def test_step_type_literal(self):
        p = Processor(type=ProcessorType.LOGGER)
        assert p.step_type == "processor"

    def test_defaults(self):
        p = Processor(type=ProcessorType.GENERIC)
        assert p.name is None
        assert p.config == {}


class TestVariableOperation:
    def test_set_operation(self):
        v = VariableOperation(operation="set", variable_name="x", value="#[1]")
        assert v.step_type == "variable_operation"
        assert v.operation == "set"
        assert v.value == "#[1]"

    def test_remove_operation(self):
        v = VariableOperation(operation="remove", variable_name="x")
        assert v.step_type == "variable_operation"
        assert v.operation == "remove"
        assert v.value is None

    def test_invalid_operation(self):
        with pytest.raises(ValidationError):
            VariableOperation(operation="invalid", variable_name="x")  # type: ignore[arg-type]


class TestTransform:
    def test_dataweave(self):
        t = Transform(type=TransformType.DATAWEAVE, expression="%dw 2.0\n---\npayload")
        assert t.step_type == "transform"
        assert t.type == TransformType.DATAWEAVE

    def test_defaults(self):
        t = Transform(type=TransformType.EXPRESSION)
        assert t.expression is None
        assert t.mime_type is None


class TestConnectorOperation:
    def test_http_request(self):
        c = ConnectorOperation(connector_type=ConnectorType.HTTP_REQUEST, operation="request")
        assert c.step_type == "connector_operation"
        assert c.connector_type == ConnectorType.HTTP_REQUEST

    def test_defaults(self):
        c = ConnectorOperation(connector_type=ConnectorType.GENERIC)
        assert c.operation is None
        assert c.config == {}


class TestRoute:
    def test_with_condition(self):
        r = Route(condition="#[true]")
        assert r.condition == "#[true]"
        assert r.steps == []

    def test_default_no_condition(self):
        r = Route()
        assert r.condition is None


class TestRouter:
    def test_choice_router(self):
        r = Router(type=RouterType.CHOICE)
        assert r.step_type == "router"
        assert r.routes == []
        assert r.default_route is None

    def test_with_routes(self):
        r = Router(
            type=RouterType.CHOICE,
            routes=[Route(condition="#[x > 0]")],
            default_route=Route(),
        )
        assert len(r.routes) == 1
        assert r.default_route is not None


class TestScope:
    def test_foreach(self):
        s = Scope(type=ScopeType.FOREACH)
        assert s.step_type == "scope"
        assert s.steps == []
        assert s.config == {}

    def test_with_config(self):
        s = Scope(type=ScopeType.FOREACH, config={"collection": "#[payload]"})
        assert s.config["collection"] == "#[payload]"


class TestErrorHandler:
    def test_propagate(self):
        eh = ErrorHandler(type=ErrorHandlerType.ON_ERROR_PROPAGATE)
        assert eh.error_type is None
        assert eh.steps == []

    def test_with_error_type(self):
        eh = ErrorHandler(type=ErrorHandlerType.ON_ERROR_CONTINUE, error_type="MULE:CONNECTIVITY")
        assert eh.error_type == "MULE:CONNECTIVITY"


class TestFlow:
    def test_minimal_flow(self):
        f = Flow(kind=FlowKind.FLOW, name="test-flow")
        assert f.trigger is None
        assert f.steps == []
        assert f.error_handlers == []

    def test_sub_flow(self):
        f = Flow(kind=FlowKind.SUB_FLOW, name="helper")
        assert f.kind == FlowKind.SUB_FLOW

    def test_requires_name(self):
        with pytest.raises(ValidationError):
            Flow(kind=FlowKind.FLOW)  # type: ignore[call-arg]


class TestMuleIR:
    def test_minimal(self):
        ir = MuleIR(
            ir_metadata=IRMetadata(source_mode=InputMode.PROJECT, source_path="/test"),
        )
        assert len(ir.flows) == 0
        assert len(ir.warnings) == 0
        assert ir.project_metadata.name is None

    def test_requires_metadata(self):
        with pytest.raises(ValidationError):
            MuleIR()  # type: ignore[call-arg]


class TestEnumValues:
    """Verify all enum members have the expected string values."""

    def test_trigger_types(self):
        assert TriggerType.HTTP_LISTENER == "http_listener"
        assert TriggerType.SCHEDULER == "scheduler"
        assert TriggerType.UNKNOWN == "unknown"

    def test_processor_types(self):
        assert ProcessorType.LOGGER == "logger"
        assert ProcessorType.SET_VARIABLE == "set_variable"
        assert ProcessorType.FLOW_REF == "flow_ref"
        assert ProcessorType.GENERIC == "generic"

    def test_router_types(self):
        assert RouterType.CHOICE == "choice"
        assert RouterType.SCATTER_GATHER == "scatter_gather"

    def test_scope_types(self):
        assert ScopeType.FOREACH == "foreach"
        assert ScopeType.TRY_SCOPE == "try_scope"
        assert ScopeType.PARALLEL_FOREACH == "parallel_foreach"

    def test_transform_types(self):
        assert TransformType.DATAWEAVE == "dataweave"
        assert TransformType.SET_PAYLOAD == "set_payload"

    def test_connector_types(self):
        assert ConnectorType.HTTP_REQUEST == "http_request"
        assert ConnectorType.DB == "db"
        assert ConnectorType.MQ == "mq"
        assert ConnectorType.GENERIC == "generic"

    def test_error_handler_types(self):
        assert ErrorHandlerType.ON_ERROR_PROPAGATE == "on_error_propagate"
        assert ErrorHandlerType.ON_ERROR_CONTINUE == "on_error_continue"

    def test_flow_kinds(self):
        assert FlowKind.FLOW == "flow"
        assert FlowKind.SUB_FLOW == "sub_flow"
