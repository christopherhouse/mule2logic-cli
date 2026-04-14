"""Shared enumerations for the migration platform."""

from enum import StrEnum


class InputMode(StrEnum):
    """Discriminator for project vs single-flow input mode."""

    PROJECT = "project"
    SINGLE_FLOW = "single_flow"


class Severity(StrEnum):
    """Severity levels for warnings, gaps, and validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class GapCategory(StrEnum):
    """Categories for migration gaps."""

    UNSUPPORTED_CONSTRUCT = "unsupported_construct"
    UNRESOLVABLE_REFERENCE = "unresolvable_reference"
    PARTIAL_SUPPORT = "partial_support"
    CONNECTOR_MISMATCH = "connector_mismatch"
    DATAWEAVE_COMPLEXITY = "dataweave_complexity"


class ConstructCategory(StrEnum):
    """Categories for MuleSoft constructs (from spec §7)."""

    TRIGGER = "trigger"
    ROUTER = "router"
    CONNECTOR = "connector"
    ERROR_HANDLER = "error_handler"
    TRANSFORM = "transform"
    SCOPE = "scope"
    FLOW_CONTROL = "flow_control"


class ValidationCategory(StrEnum):
    """Categories for validation checks."""

    MULE_INPUT = "mule_input"
    IR_INTEGRITY = "ir_integrity"
    OUTPUT_INTEGRITY = "output_integrity"
    CONNECTOR_PREFERENCE = "connector_preference"
