"""Intermediate Representation (IR) v1 for MuleSoft to Logic Apps migration.

This package provides a deterministic, JSON-serializable IR for representing
MuleSoft projects and flows. The IR is designed to be produced by a parser
and consumed by a transformer that generates Logic Apps Standard artifacts.
"""

from m2la_ir.builders import (
    build_project_ir,
    build_single_flow_ir,
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
    make_remove_variable,
    make_route,
    make_scheduler_trigger,
    make_set_variable,
    make_source_location,
    make_try_scope,
)
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
    IR_VERSION,
    ConnectorOperation,
    ErrorHandler,
    Flow,
    FlowStep,
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
from m2la_ir.serialization import from_json, to_json

__all__ = [
    # Version
    "IR_VERSION",
    # Enums
    "ConnectorType",
    "ErrorHandlerType",
    "FlowKind",
    "ProcessorType",
    "RouterType",
    "ScopeType",
    "TransformType",
    "TriggerType",
    # Models
    "ConnectorOperation",
    "ErrorHandler",
    "Flow",
    "FlowStep",
    "IRMetadata",
    "MuleIR",
    "Processor",
    "ProjectMetadata",
    "Route",
    "Router",
    "Scope",
    "SourceLocation",
    "Transform",
    "Trigger",
    "VariableOperation",
    # Serialization
    "from_json",
    "to_json",
    # Builders
    "build_project_ir",
    "build_single_flow_ir",
    "make_choice_router",
    "make_dataweave_transform",
    "make_db_operation",
    "make_error_handler",
    "make_flow",
    "make_foreach_scope",
    "make_http_request",
    "make_http_trigger",
    "make_logger",
    "make_processor",
    "make_remove_variable",
    "make_route",
    "make_scheduler_trigger",
    "make_set_variable",
    "make_source_location",
    "make_try_scope",
]
