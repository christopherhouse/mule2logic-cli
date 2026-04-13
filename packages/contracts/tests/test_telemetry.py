"""Tests for telemetry context model."""

import pytest
from pydantic import ValidationError

from m2la_contracts.telemetry import TelemetryContext


class TestTelemetryContext:
    """Tests for TelemetryContext model."""

    def test_required_fields(self) -> None:
        ctx = TelemetryContext(
            trace_id="abc123",
            span_id="span456",
            correlation_id="corr789",
        )
        assert ctx.trace_id == "abc123"
        assert ctx.span_id == "span456"
        assert ctx.correlation_id == "corr789"
        assert ctx.parent_span_id is None

    def test_with_parent_span(self) -> None:
        ctx = TelemetryContext(
            trace_id="abc123",
            span_id="span456",
            correlation_id="corr789",
            parent_span_id="parent000",
        )
        assert ctx.parent_span_id == "parent000"

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            TelemetryContext(trace_id="abc123", span_id="span456")  # type: ignore[call-arg]

    def test_serialization_roundtrip(self) -> None:
        ctx = TelemetryContext(
            trace_id="t1",
            span_id="s1",
            correlation_id="c1",
            parent_span_id="p1",
        )
        data = ctx.model_dump()
        restored = TelemetryContext.model_validate(data)
        assert restored == ctx

    def test_json_roundtrip(self) -> None:
        ctx = TelemetryContext(
            trace_id="t1",
            span_id="s1",
            correlation_id="c1",
        )
        json_str = ctx.model_dump_json()
        restored = TelemetryContext.model_validate_json(json_str)
        assert restored == ctx
