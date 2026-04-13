"""Validation report contracts."""

from pydantic import BaseModel, Field

from m2la_contracts.enums import Severity
from m2la_contracts.telemetry import TelemetryContext


class ValidationIssue(BaseModel):
    """A single validation issue found in the generated artifacts."""

    rule_id: str = Field(..., description="Machine-readable rule identifier (e.g., 'SCHEMA_001')")
    message: str = Field(..., description="Human-readable description of the issue")
    severity: Severity = Field(..., description="Issue severity")
    artifact_path: str | None = Field(default=None, description="Path to the artifact containing the issue")
    location: str | None = Field(
        default=None, description="Location within the artifact (e.g., line number or JSON path)"
    )


class ValidationReport(BaseModel):
    """Report from validating generated Logic Apps artifacts."""

    valid: bool = Field(..., description="Whether all artifacts passed validation")
    issues: list[ValidationIssue] = Field(default_factory=list, description="List of validation issues found")
    artifacts_validated: int = Field(default=0, ge=0, description="Number of artifacts that were validated")
    telemetry: TelemetryContext = Field(..., description="Telemetry context for trace correlation")
