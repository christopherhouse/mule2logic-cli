"""Map ``OrchestrationResult`` to API contract response models.

Each mapping function extracts relevant data from the agent pipeline
output and constructs the contract response model.  When the pipeline
fails or returns unexpected data, sensible defaults are used so the
API always returns a valid response shape.
"""

from __future__ import annotations

import logging
from typing import Any

from m2la_agents.models import OrchestrationResult
from m2la_contracts import (
    AnalyzeResponse,
    ArtifactManifest,
    ConstructCount,
    FlowAnalysis,
    InputMode,
    MigrationGap,
    Severity,
    TelemetryContext,
    TransformResponse,
    ValidationReport,
    Warning,
)
from m2la_contracts.enums import GapCategory, ValidationCategory
from m2la_contracts.validate import ValidationIssue

logger = logging.getLogger(__name__)


def _collect_reasoning(result: OrchestrationResult) -> list[Warning]:
    """Extract agent reasoning summaries as warnings for transparency."""
    warnings: list[Warning] = []
    for step in result.steps:
        summary = step.agent_result.reasoning_summary
        if summary:
            warnings.append(
                Warning(
                    code="AGENT_REASONING",
                    message=f"[{step.agent_result.agent_name}] {summary}",
                    severity=Severity.INFO,
                )
            )
    return warnings


def _safe_dict(value: Any) -> dict[str, Any]:
    """Ensure *value* is a dict, returning an empty dict otherwise."""
    return value if isinstance(value, dict) else {}


def _get_step_output(result: OrchestrationResult, agent_name: str) -> Any:
    """Return the output for a specific agent step, or *None*."""
    for step in result.steps:
        if step.agent_result.agent_name == agent_name:
            return step.agent_result.output
    return None


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------


def map_analyze_result(
    result: OrchestrationResult,
    mode: InputMode,
    telemetry: TelemetryContext,
) -> AnalyzeResponse:
    """Map the orchestrator result (Analyzer + Planner) to an ``AnalyzeResponse``."""
    analyzer_out = _safe_dict(_get_step_output(result, "AnalyzerAgent"))
    planner_out = _safe_dict(_get_step_output(result, "PlannerAgent"))

    # Extract flows from analyzer output
    flows: list[FlowAnalysis] = []
    raw_flows = analyzer_out.get("flows", [])
    if isinstance(raw_flows, list):
        for f in raw_flows:
            if isinstance(f, dict):
                flows.append(
                    FlowAnalysis(
                        flow_name=f.get("flow_name", "unknown"),
                        source_file=f.get("source_file", "unknown"),
                        constructs=ConstructCount(**(f.get("constructs", {}) or {})),
                        gaps=[],
                        warnings=[],
                    )
                )

    # Build construct counts from planner
    construct_summary = planner_out.get("construct_summary", {})
    constructs = ConstructCount(
        supported=planner_out.get("supported_count", 0),
        unsupported=planner_out.get("unsupported_count", 0),
        partial=planner_out.get("partial_count", 0),
        details=construct_summary if isinstance(construct_summary, dict) else {},
    )

    # Extract gaps from planner decisions
    gaps: list[MigrationGap] = []
    for decision in planner_out.get("mapping_decisions", []):
        if isinstance(decision, dict) and decision.get("status") == "unsupported":
            gaps.append(
                MigrationGap(
                    construct_name=decision.get("mule_element", "unknown"),
                    source_location="project",
                    category=GapCategory.UNSUPPORTED_CONSTRUCT,
                    severity=Severity.WARNING,
                    message=decision.get("notes", "Unsupported construct"),
                )
            )

    # Project name from analyzer
    project_name = analyzer_out.get("project_name")
    if mode == InputMode.SINGLE_FLOW:
        project_name = None

    # Reasoning summaries
    reasoning_warnings = _collect_reasoning(result)

    return AnalyzeResponse(
        mode=mode,
        project_name=project_name,
        flows=flows,
        overall_constructs=constructs,
        gaps=gaps,
        warnings=reasoning_warnings,
        telemetry=telemetry,
    )


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------


def map_transform_result(
    result: OrchestrationResult,
    mode: InputMode,
    output_directory: str,
    telemetry: TelemetryContext,
) -> TransformResponse:
    """Map the full pipeline result to a ``TransformResponse``."""
    # The transformer output may be the final_output or found in steps
    transformer_out = _safe_dict(_get_step_output(result, "TransformerAgent") or result.final_output)
    planner_out = _safe_dict(_get_step_output(result, "PlannerAgent"))
    analyzer_out = _safe_dict(_get_step_output(result, "AnalyzerAgent"))

    # Build artifact manifest from transformer output
    from m2la_contracts.common import ArtifactEntry

    raw_artifacts = transformer_out.get("artifacts", [])
    artifact_entries: list[ArtifactEntry] = []
    if isinstance(raw_artifacts, list):
        for a in raw_artifacts:
            if isinstance(a, dict):
                artifact_entries.append(
                    ArtifactEntry(
                        path=a.get("path", "unknown"),
                        artifact_type=a.get("artifact_type", "unknown"),
                        size_bytes=a.get("size_bytes"),
                    )
                )

    artifacts = ArtifactManifest(
        artifacts=artifact_entries,
        output_directory=output_directory,
        mode=mode,
    )

    # Construct counts from planner
    construct_summary = planner_out.get("construct_summary", {})
    constructs = ConstructCount(
        supported=planner_out.get("supported_count", 0),
        unsupported=planner_out.get("unsupported_count", 0),
        partial=planner_out.get("partial_count", 0),
        details=construct_summary if isinstance(construct_summary, dict) else {},
    )

    # Gaps
    gaps: list[MigrationGap] = []
    for decision in planner_out.get("mapping_decisions", []):
        if isinstance(decision, dict) and decision.get("status") == "unsupported":
            gaps.append(
                MigrationGap(
                    construct_name=decision.get("mule_element", "unknown"),
                    source_location="project",
                    category=GapCategory.UNSUPPORTED_CONSTRUCT,
                    severity=Severity.WARNING,
                    message=decision.get("notes", "Unsupported construct"),
                )
            )

    # Project name
    project_name = analyzer_out.get("project_name")
    if mode == InputMode.SINGLE_FLOW:
        project_name = None

    reasoning_warnings = _collect_reasoning(result)

    return TransformResponse(
        mode=mode,
        project_name=project_name,
        artifacts=artifacts,
        gaps=gaps,
        warnings=reasoning_warnings,
        constructs=constructs,
        telemetry=telemetry,
    )


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


def map_validate_result(
    result: OrchestrationResult,
    telemetry: TelemetryContext,
) -> ValidationReport:
    """Map the validator-only result to a ``ValidationReport``."""
    validator_out = _safe_dict(_get_step_output(result, "ValidatorAgent") or result.final_output)

    # If the validator output contains an error key or the overall status is
    # FAILURE, treat the result as invalid rather than defaulting to valid=True.
    has_error = "error" in validator_out or "error_message" in validator_out

    raw_issues = validator_out.get("issues", [])
    issues: list[ValidationIssue] = []
    if isinstance(raw_issues, list):
        for issue in raw_issues:
            if isinstance(issue, dict):
                issues.append(
                    ValidationIssue(
                        rule_id=issue.get("rule_id", "UNKNOWN"),
                        message=issue.get("message", "Validation issue"),
                        severity=Severity(issue["severity"]) if "severity" in issue else Severity.WARNING,
                        category=(
                            ValidationCategory(issue["category"])
                            if "category" in issue
                            else ValidationCategory.OUTPUT_INTEGRITY
                        ),
                        artifact_path=issue.get("artifact_path"),
                        location=issue.get("location"),
                        remediation_hint=issue.get("remediation_hint"),
                    )
                )

    if has_error:
        is_valid = False
    else:
        is_valid = validator_out.get("valid", len(issues) == 0)
    artifacts_validated = validator_out.get("artifacts_validated", 0)

    return ValidationReport(
        valid=bool(is_valid),
        issues=issues,
        artifacts_validated=artifacts_validated,
        telemetry=telemetry,
    )
