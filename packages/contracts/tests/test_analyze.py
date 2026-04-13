"""Tests for analyze request/response contracts."""

import pytest
from pydantic import ValidationError

from m2la_contracts.analyze import AnalyzeRequest, AnalyzeResponse, FlowAnalysis
from m2la_contracts.common import ConstructCount, MigrationGap, Warning
from m2la_contracts.enums import GapCategory, InputMode, Severity
from m2la_contracts.telemetry import TelemetryContext


def _make_telemetry() -> TelemetryContext:
    return TelemetryContext(trace_id="t1", span_id="s1", correlation_id="c1")


class TestAnalyzeRequest:
    """Tests for AnalyzeRequest model."""

    def test_minimal(self) -> None:
        req = AnalyzeRequest(input_path="/path/to/project")
        assert req.input_path == "/path/to/project"
        assert req.mode is None
        assert req.telemetry is None

    def test_with_mode_and_telemetry(self) -> None:
        req = AnalyzeRequest(
            input_path="/path/to/flow.xml",
            mode=InputMode.SINGLE_FLOW,
            telemetry=_make_telemetry(),
        )
        assert req.mode == InputMode.SINGLE_FLOW
        assert req.telemetry is not None
        assert req.telemetry.trace_id == "t1"

    def test_missing_input_path(self) -> None:
        with pytest.raises(ValidationError):
            AnalyzeRequest()  # type: ignore[call-arg]


class TestFlowAnalysis:
    """Tests for FlowAnalysis model."""

    def test_minimal(self) -> None:
        fa = FlowAnalysis(flow_name="main-flow", source_file="flows/main.xml")
        assert fa.flow_name == "main-flow"
        assert fa.constructs.supported == 0
        assert fa.gaps == []
        assert fa.warnings == []

    def test_with_gaps_and_warnings(self) -> None:
        gap = MigrationGap(
            construct_name="scatter-gather",
            source_location="main.xml:10",
            category=GapCategory.UNSUPPORTED_CONSTRUCT,
            severity=Severity.ERROR,
            message="not supported",
        )
        warning = Warning(code="W001", message="something")
        fa = FlowAnalysis(
            flow_name="test-flow",
            source_file="test.xml",
            constructs=ConstructCount(supported=3, unsupported=1),
            gaps=[gap],
            warnings=[warning],
        )
        assert len(fa.gaps) == 1
        assert len(fa.warnings) == 1
        assert fa.constructs.supported == 3


class TestAnalyzeResponse:
    """Tests for AnalyzeResponse model."""

    def test_minimal(self) -> None:
        resp = AnalyzeResponse(
            mode=InputMode.PROJECT,
            telemetry=_make_telemetry(),
        )
        assert resp.mode == InputMode.PROJECT
        assert resp.project_name is None
        assert resp.flows == []
        assert resp.gaps == []
        assert resp.warnings == []

    def test_missing_telemetry(self) -> None:
        with pytest.raises(ValidationError):
            AnalyzeResponse(mode=InputMode.PROJECT)  # type: ignore[call-arg]

    def test_json_roundtrip(self) -> None:
        resp = AnalyzeResponse(
            mode=InputMode.SINGLE_FLOW,
            project_name=None,
            flows=[FlowAnalysis(flow_name="f1", source_file="f1.xml")],
            telemetry=_make_telemetry(),
        )
        json_str = resp.model_dump_json()
        restored = AnalyzeResponse.model_validate_json(json_str)
        assert restored == resp
        assert len(restored.flows) == 1
