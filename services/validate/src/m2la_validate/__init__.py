"""Validation engine for MuleSoft to Logic Apps migration platform.

Validates inputs, intermediate representations, and generated outputs
across both project mode and single-flow mode.
"""

from m2la_validate.engine import validate_ir, validate_mule_input, validate_output

__all__ = [
    "validate_ir",
    "validate_mule_input",
    "validate_output",
]
