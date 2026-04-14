"""Builder/factory helpers for constructing IR nodes.

These helpers simplify IR construction in tests and future parser integration.
They provide sensible defaults while allowing full customization.
"""

from __future__ import annotations

from typing import Any

from m2la_contracts.common import Warning
from m2la_contracts.enums import InputMode
from opentelemetry import trace

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

_tracer = trace.get_tracer("m2la.ir")


def build_project_ir(
    *,
    source_path: str,
    project_name: str | None = None,
    group_id: str | None = None,
    artifact_id: str | None = None,
    version: str | None = None,
    description: str | None = None,
    flows: list[Flow] | None = None,
    warnings: list[Warning] | None = None,
) -> MuleIR:
    """Build a MuleIR for project mode.

    Args:
        source_path: Path to the MuleSoft project root.
        project_name: Project name from pom.xml.
        group_id: Maven group ID.
        artifact_id: Maven artifact ID.
        version: Project version.
        description: Project description.
        flows: List of flows in the project.
        warnings: Warnings emitted during construction.

    Returns:
        A fully constructed MuleIR for project mode.
    """
    with _tracer.start_as_current_span("m2la.ir.build_project") as span:
        resolved_flows = flows or []
        span.set_attribute("ir.flows_count", len(resolved_flows))
        span.set_attribute("ir.steps_count", sum(len(f.steps) for f in resolved_flows))
        return MuleIR(
            ir_metadata=IRMetadata(
                source_mode=InputMode.PROJECT,
                source_path=source_path,
            ),
            project_metadata=ProjectMetadata(
                name=project_name,
                group_id=group_id,
                artifact_id=artifact_id,
                version=version,
                description=description,
            ),
            flows=resolved_flows,
            warnings=warnings or [],
        )


def build_single_flow_ir(
    *,
    source_path: str,
    flows: list[Flow] | None = None,
    warnings: list[Warning] | None = None,
) -> MuleIR:
    """Build a MuleIR for single-flow mode.

    In single-flow mode, project metadata is empty and warnings are typically
    present for unresolvable external references.

    Args:
        source_path: Path to the standalone flow XML file.
        flows: Flows extracted from the file.
        warnings: Warnings for missing context (connector configs, properties, etc.).

    Returns:
        A MuleIR for single-flow mode with empty project metadata.
    """
    with _tracer.start_as_current_span("m2la.ir.build_single_flow") as span:
        resolved_flows = flows or []
        span.set_attribute("ir.flows_count", len(resolved_flows))
        span.set_attribute("ir.steps_count", sum(len(f.steps) for f in resolved_flows))
        return MuleIR(
            ir_metadata=IRMetadata(
                source_mode=InputMode.SINGLE_FLOW,
                source_path=source_path,
            ),
            project_metadata=ProjectMetadata(),
            flows=resolved_flows,
            warnings=warnings or [],
        )


def make_source_location(file: str, line: int | None = None, column: int | None = None) -> SourceLocation:
    """Create a SourceLocation."""
    return SourceLocation(file=file, line=line, column=column)


def make_http_trigger(
    *,
    path: str = "/",
    method: str = "GET",
    config_ref: str | None = None,
    source_location: SourceLocation | None = None,
) -> Trigger:
    """Create an HTTP listener trigger."""
    config: dict[str, Any] = {"path": path, "method": method}
    if config_ref is not None:
        config["config_ref"] = config_ref
    return Trigger(
        type=TriggerType.HTTP_LISTENER,
        config=config,
        source_location=source_location,
    )


def make_scheduler_trigger(
    *,
    frequency: str = "1000",
    time_unit: str = "MILLISECONDS",
    source_location: SourceLocation | None = None,
) -> Trigger:
    """Create a scheduler trigger."""
    return Trigger(
        type=TriggerType.SCHEDULER,
        config={"frequency": frequency, "timeUnit": time_unit},
        source_location=source_location,
    )


def make_processor(
    type: ProcessorType,
    *,
    name: str | None = None,
    config: dict[str, Any] | None = None,
    source_location: SourceLocation | None = None,
) -> Processor:
    """Create a generic processor."""
    return Processor(
        type=type,
        name=name,
        config=config or {},
        source_location=source_location,
    )


def make_logger(
    *,
    message: str = "",
    level: str = "INFO",
    source_location: SourceLocation | None = None,
) -> Processor:
    """Create a logger processor."""
    return make_processor(
        ProcessorType.LOGGER,
        config={"message": message, "level": level},
        source_location=source_location,
    )


def make_set_variable(
    *,
    variable_name: str,
    value: str,
    source_location: SourceLocation | None = None,
) -> VariableOperation:
    """Create a set-variable operation."""
    return VariableOperation(
        operation="set",
        variable_name=variable_name,
        value=value,
        source_location=source_location,
    )


def make_remove_variable(
    *,
    variable_name: str,
    source_location: SourceLocation | None = None,
) -> VariableOperation:
    """Create a remove-variable operation."""
    return VariableOperation(
        operation="remove",
        variable_name=variable_name,
        source_location=source_location,
    )


def make_dataweave_transform(
    *,
    expression: str,
    mime_type: str = "application/json",
    source_location: SourceLocation | None = None,
) -> Transform:
    """Create a DataWeave transform step."""
    return Transform(
        type=TransformType.DATAWEAVE,
        expression=expression,
        mime_type=mime_type,
        source_location=source_location,
    )


def make_http_request(
    *,
    method: str = "GET",
    url: str = "",
    config_ref: str | None = None,
    config: dict[str, Any] | None = None,
    source_location: SourceLocation | None = None,
) -> ConnectorOperation:
    """Create an HTTP request connector operation."""
    op_config: dict[str, Any] = config or {}
    op_config.setdefault("method", method)
    if url:
        op_config["url"] = url
    if config_ref is not None:
        op_config["config_ref"] = config_ref
    return ConnectorOperation(
        connector_type=ConnectorType.HTTP_REQUEST,
        operation="request",
        config=op_config,
        source_location=source_location,
    )


def make_db_operation(
    *,
    operation: str = "select",
    query: str = "",
    config_ref: str | None = None,
    source_location: SourceLocation | None = None,
) -> ConnectorOperation:
    """Create a database connector operation."""
    config: dict[str, Any] = {"query": query}
    if config_ref is not None:
        config["config_ref"] = config_ref
    return ConnectorOperation(
        connector_type=ConnectorType.DB,
        operation=operation,
        config=config,
        source_location=source_location,
    )


def make_choice_router(
    *,
    routes: list[Route] | None = None,
    default_route: Route | None = None,
    source_location: SourceLocation | None = None,
) -> Router:
    """Create a choice router."""
    return Router(
        type=RouterType.CHOICE,
        routes=routes or [],
        default_route=default_route,
        source_location=source_location,
    )


def make_route(
    *,
    condition: str | None = None,
    steps: list[FlowStep] | None = None,
) -> Route:
    """Create a route for a router."""
    return Route(condition=condition, steps=steps or [])


def make_foreach_scope(
    *,
    collection: str = "#[payload]",
    steps: list[FlowStep] | None = None,
    source_location: SourceLocation | None = None,
) -> Scope:
    """Create a foreach scope."""
    return Scope(
        type=ScopeType.FOREACH,
        steps=steps or [],
        config={"collection": collection},
        source_location=source_location,
    )


def make_try_scope(
    *,
    steps: list[FlowStep] | None = None,
    source_location: SourceLocation | None = None,
) -> Scope:
    """Create a try scope."""
    return Scope(
        type=ScopeType.TRY_SCOPE,
        steps=steps or [],
        source_location=source_location,
    )


def make_error_handler(
    *,
    handler_type: ErrorHandlerType,
    error_type: str | None = None,
    steps: list[FlowStep] | None = None,
    source_location: SourceLocation | None = None,
) -> ErrorHandler:
    """Create an error handler."""
    return ErrorHandler(
        type=handler_type,
        error_type=error_type,
        steps=steps or [],
        source_location=source_location,
    )


def make_flow(
    *,
    name: str,
    kind: FlowKind = FlowKind.FLOW,
    trigger: Trigger | None = None,
    steps: list[FlowStep] | None = None,
    error_handlers: list[ErrorHandler] | None = None,
    source_location: SourceLocation | None = None,
) -> Flow:
    """Create a flow or sub-flow."""
    return Flow(
        kind=kind,
        name=name,
        trigger=trigger,
        steps=steps or [],
        error_handlers=error_handlers or [],
        source_location=source_location,
    )
