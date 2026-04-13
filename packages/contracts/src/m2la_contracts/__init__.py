"""Shared contracts and schemas for the MuleSoft to Logic Apps migration platform.

This package provides Pydantic models, enumerations, and helpers used by both
the Python backend (FastAPI) and the TypeScript CLI.
"""

from m2la_contracts.analyze import AnalyzeRequest, AnalyzeResponse, FlowAnalysis
from m2la_contracts.common import ArtifactEntry, ArtifactManifest, ConstructCount, MigrationGap, Warning
from m2la_contracts.enums import ConstructCategory, GapCategory, InputMode, Severity
from m2la_contracts.helpers import detect_input_mode
from m2la_contracts.telemetry import TelemetryContext
from m2la_contracts.transform import TransformRequest, TransformResponse
from m2la_contracts.validate import ValidateRequest, ValidationIssue, ValidationReport

__all__ = [
    # Enums
    "ConstructCategory",
    "GapCategory",
    "InputMode",
    "Severity",
    # Telemetry
    "TelemetryContext",
    # Common models
    "ArtifactEntry",
    "ArtifactManifest",
    "ConstructCount",
    "MigrationGap",
    "Warning",
    # Analyze
    "AnalyzeRequest",
    "AnalyzeResponse",
    "FlowAnalysis",
    # Transform
    "TransformRequest",
    "TransformResponse",
    # Validate
    "ValidateRequest",
    "ValidationIssue",
    "ValidationReport",
    # Helpers
    "detect_input_mode",
]
