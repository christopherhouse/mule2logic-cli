"""Core IR models forming the intermediate representation tree.

The IR is a deterministic, JSON-serializable representation of a MuleSoft project
or single flow. It is designed to be produced by a parser and consumed by a
transformer that generates Logic Apps Standard artifacts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from m2la_contracts.common import Warning
from m2la_contracts.enums import InputMode
from pydantic import BaseModel, Field

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

IR_VERSION = "1.0"
"""Current IR schema version."""


class IRMetadata(BaseModel):
    """Metadata about the IR generation itself."""

    version: str = Field(default=IR_VERSION, description="IR schema version")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the IR was generated",
    )
    source_mode: InputMode = Field(..., description="Whether IR was built from a project or single flow")
    source_path: str = Field(..., description="Path to the source project or flow file")


class ProjectMetadata(BaseModel):
    """MuleSoft project metadata extracted from pom.xml.

    All fields are optional to support single-flow mode where no pom.xml exists.
    """

    name: str | None = Field(default=None, description="Project name from pom.xml")
    group_id: str | None = Field(default=None, description="Maven group ID")
    artifact_id: str | None = Field(default=None, description="Maven artifact ID")
    version: str | None = Field(default=None, description="Project version")
    description: str | None = Field(default=None, description="Project description")


class SourceLocation(BaseModel):
    """Location in a source XML file for traceability."""

    file: str = Field(..., description="Relative path to the source file")
    line: int | None = Field(default=None, ge=1, description="Line number (1-based)")
    column: int | None = Field(default=None, ge=1, description="Column number (1-based)")


class Trigger(BaseModel):
    """A flow trigger (e.g., HTTP listener, scheduler)."""

    type: TriggerType = Field(..., description="Type of trigger")
    config: dict[str, Any] = Field(default_factory=dict, description="Trigger-specific configuration")
    source_location: SourceLocation | None = Field(default=None, description="Source XML location")


class Processor(BaseModel):
    """A message processor (e.g., logger, set-variable, flow-ref)."""

    step_type: Literal["processor"] = "processor"
    type: ProcessorType = Field(..., description="Type of processor")
    name: str | None = Field(default=None, description="Optional processor name/label")
    config: dict[str, Any] = Field(default_factory=dict, description="Processor-specific configuration")
    source_location: SourceLocation | None = Field(default=None, description="Source XML location")


class VariableOperation(BaseModel):
    """A variable set or remove operation."""

    step_type: Literal["variable_operation"] = "variable_operation"
    operation: Literal["set", "remove"] = Field(..., description="Whether to set or remove the variable")
    variable_name: str = Field(..., description="Name of the variable")
    value: str | None = Field(default=None, description="Value expression (None for remove operations)")
    source_location: SourceLocation | None = Field(default=None, description="Source XML location")


class Transform(BaseModel):
    """A data transformation step (DataWeave, set-payload, expression)."""

    step_type: Literal["transform"] = "transform"
    type: TransformType = Field(..., description="Type of transformation")
    expression: str | None = Field(default=None, description="Transformation expression or body")
    mime_type: str | None = Field(default=None, description="Output MIME type (e.g., 'application/json')")
    source_location: SourceLocation | None = Field(default=None, description="Source XML location")


class ConnectorOperation(BaseModel):
    """An outbound connector operation (HTTP request, DB query, MQ publish, etc.)."""

    step_type: Literal["connector_operation"] = "connector_operation"
    connector_type: ConnectorType = Field(..., description="Type of connector")
    operation: str | None = Field(default=None, description="Operation name (e.g., 'request', 'select', 'publish')")
    config: dict[str, Any] = Field(default_factory=dict, description="Connector-specific configuration")
    source_location: SourceLocation | None = Field(default=None, description="Source XML location")


class Route(BaseModel):
    """A single route within a choice router."""

    condition: str | None = Field(default=None, description="Route condition expression (None for default route)")
    steps: list[FlowStep] = Field(default_factory=list, description="Processors within this route")


class Router(BaseModel):
    """A message router (choice, scatter-gather, etc.)."""

    step_type: Literal["router"] = "router"
    type: RouterType = Field(..., description="Type of router")
    routes: list[Route] = Field(default_factory=list, description="Named routes with conditions")
    default_route: Route | None = Field(default=None, description="Default/otherwise route")
    source_location: SourceLocation | None = Field(default=None, description="Source XML location")


class Scope(BaseModel):
    """A processing scope (foreach, try, until-successful, etc.)."""

    step_type: Literal["scope"] = "scope"
    type: ScopeType = Field(..., description="Type of scope")
    steps: list[FlowStep] = Field(default_factory=list, description="Processors within this scope")
    config: dict[str, Any] = Field(default_factory=dict, description="Scope-specific configuration")
    source_location: SourceLocation | None = Field(default=None, description="Source XML location")


class ErrorHandler(BaseModel):
    """An error handler attached to a flow or try scope."""

    type: ErrorHandlerType = Field(..., description="Type of error handler")
    error_type: str | None = Field(default=None, description="Error type pattern to match (e.g., 'MULE:CONNECTIVITY')")
    steps: list[FlowStep] = Field(default_factory=list, description="Processors to execute on error")
    source_location: SourceLocation | None = Field(default=None, description="Source XML location")


# FlowStep is a discriminated union of all step types
FlowStep = Annotated[
    Processor | VariableOperation | Transform | ConnectorOperation | Router | Scope,
    Field(discriminator="step_type"),
]
"""A single step in a flow — discriminated union over step_type."""


class Flow(BaseModel):
    """A Mule flow or sub-flow."""

    kind: FlowKind = Field(..., description="Whether this is a flow or sub-flow")
    name: str = Field(..., description="Flow name")
    trigger: Trigger | None = Field(default=None, description="Flow trigger (only for top-level flows)")
    steps: list[FlowStep] = Field(default_factory=list, description="Ordered list of processing steps")
    error_handlers: list[ErrorHandler] = Field(default_factory=list, description="Error handlers for this flow")
    source_location: SourceLocation | None = Field(default=None, description="Source XML location")


class MuleIR(BaseModel):
    """Root of the intermediate representation.

    Represents either a full MuleSoft project (project mode) or a single
    flow file (single-flow mode).
    """

    ir_metadata: IRMetadata = Field(..., description="IR generation metadata")
    project_metadata: ProjectMetadata = Field(
        default_factory=ProjectMetadata, description="Project metadata (empty in single-flow mode)"
    )
    flows: list[Flow] = Field(default_factory=list, description="All flows and sub-flows")
    warnings: list[Warning] = Field(default_factory=list, description="Warnings emitted during IR construction")
