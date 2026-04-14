"""Transform route — converts a MuleSoft project or single flow to Logic Apps artifacts."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from m2la_agents import MigrationOrchestrator
from m2la_contracts import (
    InputMode,
    TelemetryContext,
    TransformRequest,
    TransformResponse,
    detect_input_mode,
)

from m2la_api.dependencies import get_chat_client
from m2la_api.models.errors import ApiError
from m2la_api.services.result_mapper import map_transform_result

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/transform", response_model=TransformResponse)
async def transform(
    request: TransformRequest,
    chat_client: Any = Depends(get_chat_client),
) -> TransformResponse:
    """Transform a MuleSoft project or single flow XML into Logic Apps artifacts.

    Runs the full 5-agent pipeline (Analyzer → Planner → Transformer →
    Validator → RepairAdvisor) through the MigrationOrchestrator.
    """
    mode: InputMode = request.mode if request.mode is not None else detect_input_mode(request.input_path)
    output_dir = request.output_directory or "./output"

    telemetry = request.telemetry or TelemetryContext(
        trace_id=uuid.uuid4().hex[:16],
        span_id=uuid.uuid4().hex[:8],
        correlation_id=str(uuid.uuid4()),
    )

    orchestrator = MigrationOrchestrator(
        client=chat_client,
        include_repair=True,
    )

    try:
        result = await asyncio.to_thread(
            orchestrator.run,
            request.input_path,
            input_mode=mode,
            output_directory=output_dir,
            correlation_id=telemetry.correlation_id,
            trace_id=telemetry.trace_id,
            span_id=telemetry.span_id,
        )
    except Exception as exc:
        logger.exception("Transform pipeline failed")
        raise ApiError(
            status_code=503,
            error_code="PIPELINE_ERROR",
            message="Transform pipeline failed",
            detail=str(exc),
        ) from exc

    return map_transform_result(result, mode, output_dir, telemetry)
