"""Tests for validation report contracts."""

import pytest
from pydantic import ValidationError

from m2la_contracts.enums import Severity
from m2la_contracts.telemetry import TelemetryContext
from m2la_contracts.validate import ValidationIssue, ValidationReport


def _make_telemetry() -> TelemetryContext:
    return TelemetryContext(trace_id="t1", span_id="s1", correlation_id="c1")


class TestValidationIssue:
    """Tests for ValidationIssue model."""

    def test_full(self) -> None:
        issue = ValidationIssue(
            rule_id="SCHEMA_001",
            message="Invalid schema",
            severity=Severity.ERROR,
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
