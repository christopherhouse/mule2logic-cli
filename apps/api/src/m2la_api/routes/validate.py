"""Validate route — validates generated Logic Apps artifacts."""

import uuid

from fastapi import APIRouter
from m2la_contracts import TelemetryContext, ValidateRequest, ValidationReport

router = APIRouter()


@router.post("/validate", response_model=ValidationReport)
async def validate(request: ValidateRequest) -> ValidationReport:
    """Validate generated Logic Apps artifacts.

    Returns a placeholder validation report conforming to the contract.
    """
    telemetry = request.telemetry or TelemetryContext(
        trace_id=uuid.uuid4().hex[:16],
        span_id=uuid.uuid4().hex[:8],
        correlation_id=str(uuid.uuid4()),
    )

    return ValidationReport(
        valid=True,
        issues=[],
        artifacts_validated=0,
        telemetry=telemetry,
    )
