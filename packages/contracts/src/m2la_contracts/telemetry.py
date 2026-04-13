"""Telemetry correlation metadata for end-to-end observability (spec §9)."""

from pydantic import BaseModel, Field


class TelemetryContext(BaseModel):
    """Telemetry correlation metadata propagated across CLI, API, and services."""

    trace_id: str = Field(..., description="OpenTelemetry trace ID")
    span_id: str = Field(..., description="OpenTelemetry span ID")
    correlation_id: str = Field(..., description="Platform correlation ID (UUID)")
    parent_span_id: str | None = Field(default=None, description="Parent span ID for nested operations")
