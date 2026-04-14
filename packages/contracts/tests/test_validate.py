"""Tests for validation report contracts."""

import pytest
from pydantic import ValidationError

from m2la_contracts.enums import Severity, ValidationCategory
from m2la_contracts.telemetry import TelemetryContext
from m2la_contracts.validate import ValidateRequest, ValidationIssue, ValidationReport


def _make_telemetry() -> TelemetryContext:
    return TelemetryContext(trace_id="t1", span_id="s1", correlation_id="c1")


class TestValidateRequest:
    """Tests for ValidateRequest model."""

    def test_minimal(self) -> None:
        req = ValidateRequest(output_directory="/tmp/output")
        assert req.output_directory == "/tmp/output"
        assert req.telemetry is None

    def test_with_telemetry(self) -> None:
        req = ValidateRequest(
            output_directory="/tmp/output",
            telemetry=_make_telemetry(),
        )
        assert req.telemetry is not None
        assert req.telemetry.trace_id == "t1"

    def test_missing_output_directory(self) -> None:
        with pytest.raises(ValidationError):
            ValidateRequest()  # type: ignore[call-arg]

    def test_json_roundtrip(self) -> None:
        req = ValidateRequest(output_directory="/tmp/output", telemetry=_make_telemetry())
        json_str = req.model_dump_json()
        restored = ValidateRequest.model_validate_json(json_str)
        assert restored == req


class TestValidationIssue:
    """Tests for ValidationIssue model."""

    def test_full(self) -> None:
        issue = ValidationIssue(
            rule_id="SCHEMA_001",
            message="Invalid schema",
            severity=Severity.ERROR,
            category=ValidationCategory.OUTPUT_INTEGRITY,
            artifact_path="workflow.json",
            location="$.definition.triggers",
        )
        assert issue.rule_id == "SCHEMA_001"
        assert issue.artifact_path == "workflow.json"

    def test_optional_fields_default_none(self) -> None:
        issue = ValidationIssue(
            rule_id="TEST_001",
            message="test",
            severity=Severity.WARNING,
            category=ValidationCategory.OUTPUT_INTEGRITY,
        )
        assert issue.artifact_path is None
        assert issue.location is None

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            ValidationIssue(rule_id="X")  # type: ignore[call-arg]


class TestValidationReport:
    """Tests for ValidationReport model."""

    def test_valid_report(self) -> None:
        report = ValidationReport(
            valid=True,
            artifacts_validated=5,
            telemetry=_make_telemetry(),
        )
        assert report.valid is True
        assert report.issues == []
        assert report.artifacts_validated == 5

    def test_invalid_report_with_issues(self) -> None:
        issue = ValidationIssue(
            rule_id="SCHEMA_001",
            message="bad schema",
            severity=Severity.ERROR,
            category=ValidationCategory.OUTPUT_INTEGRITY,
        )
        report = ValidationReport(
            valid=False,
            issues=[issue],
            artifacts_validated=3,
            telemetry=_make_telemetry(),
        )
        assert report.valid is False
        assert len(report.issues) == 1

    def test_negative_artifacts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ValidationReport(
                valid=True,
                artifacts_validated=-1,
                telemetry=_make_telemetry(),
            )

    def test_json_roundtrip(self) -> None:
        report = ValidationReport(
            valid=True,
            artifacts_validated=2,
            telemetry=_make_telemetry(),
        )
        json_str = report.model_dump_json()
        restored = ValidationReport.model_validate_json(json_str)
        assert restored == report
