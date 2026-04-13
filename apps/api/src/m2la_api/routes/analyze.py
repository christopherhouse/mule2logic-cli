"""Analyze route — accepts a MuleSoft project or single flow for analysis."""

import uuid

from fastapi import APIRouter
from m2la_contracts import (
    AnalyzeRequest,
    AnalyzeResponse,
    ConstructCount,
    InputMode,
    TelemetryContext,
    detect_input_mode,
)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze a MuleSoft project or single flow XML.

    Auto-detects input mode from the path when ``mode`` is not provided.
    Returns a placeholder response conforming to the contract.
    """
    mode: InputMode = request.mode if request.mode is not None else detect_input_mode(request.input_path)

    telemetry = request.telemetry or TelemetryContext(
        trace_id=uuid.uuid4().hex[:16],
        span_id=uuid.uuid4().hex[:8],
        correlation_id=str(uuid.uuid4()),
    )

    return AnalyzeResponse(
        mode=mode,
        project_name=None if mode == InputMode.SINGLE_FLOW else "placeholder-project",
        flows=[],
        overall_constructs=ConstructCount(),
        gaps=[],
        warnings=[],
        telemetry=telemetry,
    )
