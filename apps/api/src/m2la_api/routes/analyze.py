"""Analyze route — accepts a MuleSoft project or single flow for analysis."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from m2la_agents import AnalyzerAgent, MigrationOrchestrator, PlannerAgent
from m2la_contracts import (
    AnalyzeRequest,
    AnalyzeResponse,
    InputMode,
    TelemetryContext,
    detect_input_mode,
)

from m2la_api.dependencies import get_chat_client
from m2la_api.models.errors import ApiError
from m2la_api.services.result_mapper import map_analyze_result

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    chat_client: Any = Depends(get_chat_client),
) -> AnalyzeResponse:
    """Analyze a MuleSoft project or single flow XML.

    Runs the AnalyzerAgent + PlannerAgent through the MigrationOrchestrator
    and returns a real analysis with discovered flows, construct counts,
    gaps, warnings, and agent reasoning summaries.
    """
    mode: InputMode = request.mode if request.mode is not None else detect_input_mode(request.input_path)

    telemetry = request.telemetry or TelemetryContext(
        trace_id=uuid.uuid4().hex[:16],
        span_id=uuid.uuid4().hex[:8],
        correlation_id=str(uuid.uuid4()),
    )

    orchestrator = MigrationOrchestrator(
        client=chat_client,
        agents=[AnalyzerAgent(), PlannerAgent()],
        include_repair=False,
    )

    try:
        result = await asyncio.to_thread(
            orchestrator.run,
            request.input_path,
            input_mode=mode,
            correlation_id=telemetry.correlation_id,
            trace_id=telemetry.trace_id,
            span_id=telemetry.span_id,
        )
    except Exception as exc:
        logger.exception("Analyze pipeline failed")
        raise ApiError(
            status_code=503,
            error_code="PIPELINE_ERROR",
            message="Analysis pipeline failed",
            detail=str(exc),
        ) from exc

    return map_analyze_result(result, mode, telemetry)
