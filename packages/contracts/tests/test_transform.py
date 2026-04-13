"""Tests for transform request/response contracts."""

import pytest
from pydantic import ValidationError

from m2la_contracts.common import ArtifactEntry, ArtifactManifest
from m2la_contracts.enums import InputMode
from m2la_contracts.telemetry import TelemetryContext
from m2la_contracts.transform import TransformRequest, TransformResponse


def _make_telemetry() -> TelemetryContext:
    return TelemetryContext(trace_id="t1", span_id="s1", correlation_id="c1")


class TestTransformRequest:
    """Tests for TransformRequest model."""

    def test_minimal(self) -> None:
        req = TransformRequest(input_path="/path/to/project")
        assert req.input_path == "/path/to/project"
        assert req.mode is None
        assert req.output_directory is None
        assert req.telemetry is None

    def test_with_all_fields(self) -> None:
        req = TransformRequest(
            input_path="/path/to/flow.xml",
            mode=InputMode.SINGLE_FLOW,
            output_directory="/out",
            telemetry=_make_telemetry(),
        )
        assert req.output_directory == "/out"
        assert req.mode == InputMode.SINGLE_FLOW

    def test_missing_input_path(self) -> None:
        with pytest.raises(ValidationError):
            TransformRequest()  # type: ignore[call-arg]


class TestTransformResponse:
    """Tests for TransformResponse model."""

    def test_minimal(self) -> None:
        manifest = ArtifactManifest(output_directory="./out", mode=InputMode.PROJECT)
        resp = TransformResponse(
            mode=InputMode.PROJECT,
            artifacts=manifest,
            telemetry=_make_telemetry(),
        )
        assert resp.mode == InputMode.PROJECT
        assert resp.artifacts.output_directory == "./out"
        assert resp.gaps == []
        assert resp.warnings == []

    def test_with_artifacts(self) -> None:
        entry = ArtifactEntry(path="workflow.json", artifact_type="workflow", size_bytes=512)
        manifest = ArtifactManifest(
            artifacts=[entry],
            output_directory="./out",
            mode=InputMode.SINGLE_FLOW,
        )
        resp = TransformResponse(
            mode=InputMode.SINGLE_FLOW,
            artifacts=manifest,
            telemetry=_make_telemetry(),
        )
        assert len(resp.artifacts.artifacts) == 1
        assert resp.artifacts.artifacts[0].size_bytes == 512

    def test_missing_artifacts(self) -> None:
        with pytest.raises(ValidationError):
            TransformResponse(mode=InputMode.PROJECT, telemetry=_make_telemetry())  # type: ignore[call-arg]

    def test_json_roundtrip(self) -> None:
        manifest = ArtifactManifest(output_directory="./out", mode=InputMode.PROJECT)
        resp = TransformResponse(
            mode=InputMode.PROJECT,
            artifacts=manifest,
            telemetry=_make_telemetry(),
        )
        json_str = resp.model_dump_json()
        restored = TransformResponse.model_validate_json(json_str)
        assert restored == resp
