"""Validation engine — orchestrates all validation rules.

Provides top-level entry points for validating Mule inputs, IR, and generated outputs.
Returns structured :class:`~m2la_contracts.validate.ValidationReport` objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from m2la_contracts.enums import InputMode, Severity
from m2la_contracts.validate import ValidationIssue, ValidationReport
from m2la_ir.models import MuleIR
from opentelemetry import metrics, trace

from m2la_validate.rules.ir_integrity import validate_ir as _validate_ir_rules
from m2la_validate.rules.mule_input import validate_mule_input as _validate_mule_rules
from m2la_validate.rules.output_integrity import validate_output as _validate_output_rules

_tracer = trace.get_tracer("m2la.validate")
_meter = metrics.get_meter("m2la.validate")
_validation_issues = _meter.create_counter(
    "m2la.validation.issues", description="Validation issues detected", unit="1"
)
_validation_runs = _meter.create_counter("m2la.validation.runs", description="Validation runs", unit="1")


def _build_report(issues: list[ValidationIssue], artifacts_validated: int = 1) -> ValidationReport:
    """Build a ValidationReport from a list of issues.

    The report is marked invalid if any issue has severity ERROR or CRITICAL.
    """
    has_errors = any(issue.severity in (Severity.ERROR, Severity.CRITICAL) for issue in issues)
    return ValidationReport(
        valid=not has_errors,
        issues=issues,
        artifacts_validated=artifacts_validated,
    )


def _emit_validation_metrics(report: ValidationReport, phase: str) -> None:
    """Emit OTel metrics for a validation run."""
    _validation_runs.add(1, {"phase": phase, "valid": str(report.valid)})
    for issue in report.issues:
        _validation_issues.add(1, {"phase": phase, "severity": issue.severity.value})


def validate_mule_input(input_path: Path, mode: InputMode) -> ValidationReport:
    """Validate Mule project or single-flow XML input.

    Args:
        input_path: Path to the Mule project directory or single flow XML file.
        mode: Input mode (project or single_flow).

    Returns:
        A ValidationReport with any issues found.
    """
    with _tracer.start_as_current_span("m2la.validate.mule_input") as span:
        span.set_attribute("validation.phase", "mule_input")
        issues = _validate_mule_rules(input_path, mode)
        report = _build_report(issues)
        span.set_attribute("issues.count", len(issues))
        span.set_attribute("validation.valid", report.valid)
        _emit_validation_metrics(report, "mule_input")
        return report


def validate_ir(ir: MuleIR) -> ValidationReport:
    """Validate IR integrity.

    Args:
        ir: The intermediate representation to validate.

    Returns:
        A ValidationReport with any issues found.
    """
    with _tracer.start_as_current_span("m2la.validate.ir") as span:
        span.set_attribute("validation.phase", "ir")
        issues = _validate_ir_rules(ir)
        report = _build_report(issues, artifacts_validated=len(ir.flows))
        span.set_attribute("issues.count", len(issues))
        span.set_attribute("validation.valid", report.valid)
        _emit_validation_metrics(report, "ir")
        return report


def validate_output(
    output: Path | dict[str, Any],
    mode: InputMode,
) -> ValidationReport:
    """Validate generated Logic Apps output.

    Args:
        output: Path to the output directory (project mode) or workflow JSON dict
            (single-flow mode).
        mode: Input mode (project or single_flow).

    Returns:
        A ValidationReport with any issues found.
    """
    with _tracer.start_as_current_span("m2la.validate.output") as span:
        span.set_attribute("validation.phase", "output")
        issues = _validate_output_rules(output, mode)
        # Count validated artifacts
        if mode == InputMode.PROJECT and isinstance(output, Path):
            count = 0
            for f in _PROJECT_FILES:
                if (output / f).is_file():
                    count += 1
            wf_dir = output / "workflows"
            if wf_dir.is_dir():
                for d in wf_dir.iterdir():
                    if d.is_dir() and (d / "workflow.json").is_file():
                        count += 1
        else:
            count = 1

        report = _build_report(issues, artifacts_validated=count)
        span.set_attribute("issues.count", len(issues))
        span.set_attribute("validation.valid", report.valid)
        _emit_validation_metrics(report, "output")
        return report


_PROJECT_FILES = ["host.json", "connections.json", "parameters.json", ".env"]


def validate_all(
    *,
    input_path: Path | None = None,
    mode: InputMode,
    ir: MuleIR | None = None,
    output: Path | dict[str, Any] | None = None,
) -> ValidationReport:
    """Run all applicable validation stages and return a combined report.

    This is a convenience function that runs input, IR, and output validation
    in sequence and merges results into a single report.

    Args:
        input_path: Path to the Mule input (optional).
        mode: Input mode (project or single_flow).
        ir: The intermediate representation (optional).
        output: The generated output — Path or dict (optional).

    Returns:
        A combined ValidationReport.
    """
    all_issues: list[ValidationIssue] = []
    total_validated = 0

    if input_path is not None:
        report = validate_mule_input(input_path, mode)
        all_issues.extend(report.issues)
        total_validated += report.artifacts_validated

    if ir is not None:
        report = validate_ir(ir)
        all_issues.extend(report.issues)
        total_validated += report.artifacts_validated

    if output is not None:
        report = validate_output(output, mode)
        all_issues.extend(report.issues)
        total_validated += report.artifacts_validated

    return _build_report(all_issues, artifacts_validated=total_validated)
