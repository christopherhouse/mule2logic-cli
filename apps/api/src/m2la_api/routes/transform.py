"""Transform route — converts a MuleSoft project or single flow to Logic Apps artifacts."""

import uuid

from fastapi import APIRouter
from m2la_contracts import (
    ArtifactManifest,
    ConstructCount,
    InputMode,
    TelemetryContext,
    TransformRequest,
    TransformResponse,
    detect_input_mode,
)

router = APIRouter()


@router.post("/transform", response_model=TransformResponse)
async def transform(request: TransformRequest) -> TransformResponse:
    """Transform a MuleSoft project or single flow XML into Logic Apps artifacts.

    Auto-detects input mode from the path when ``mode`` is not provided.
    Returns a placeholder response conforming to the contract.
    """
    mode: InputMode = request.mode if request.mode is not None else detect_input_mode(request.input_path)
    output_dir = request.output_directory or "./output"

    telemetry = request.telemetry or TelemetryContext(
        trace_id=uuid.uuid4().hex[:16],
        span_id=uuid.uuid4().hex[:8],
        correlation_id=str(uuid.uuid4()),
    )

    return TransformResponse(
        mode=mode,
        project_name=None if mode == InputMode.SINGLE_FLOW else "placeholder-project",
        artifacts=ArtifactManifest(
            artifacts=[],
            output_directory=output_dir,
            mode=mode,
        ),
        gaps=[],
        warnings=[],
        constructs=ConstructCount(),
        telemetry=telemetry,
    )
