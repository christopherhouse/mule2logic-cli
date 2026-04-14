"""Validate route — validates generated Logic Apps artifacts."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from m2la_agents import MigrationOrchestrator, ValidatorAgent
from m2la_contracts import TelemetryContext, ValidateRequest, ValidationReport

from m2la_api.dependencies import get_chat_client
from m2la_api.models.errors import ApiError
from m2la_api.services.result_mapper import map_validate_result

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/validate", response_model=ValidationReport)
async def validate(
    request: ValidateRequest,
    chat_client: Any = Depends(get_chat_client),
) -> ValidationReport:
    """Validate generated Logic Apps artifacts.

    Runs the ValidatorAgent through the MigrationOrchestrator and returns
    a real validation report.
    """
    telemetry = request.telemetry or TelemetryContext(
        trace_id=uuid.uuid4().hex[:16],
        span_id=uuid.uuid4().hex[:8],
        correlation_id=str(uuid.uuid4()),
    )

    orchestrator = MigrationOrchestrator(
        client=chat_client,
        agents=[ValidatorAgent()],
        include_repair=False,
    )

    try:
        result = await asyncio.to_thread(
            orchestrator.run,
            request.output_directory,
            correlation_id=telemetry.correlation_id,
            trace_id=telemetry.trace_id,
            span_id=telemetry.span_id,
        )
    except Exception as exc:
        logger.exception("Validate pipeline failed")
        raise ApiError(
            status_code=503,
            error_code="PIPELINE_ERROR",
            message="Validation pipeline failed",
            detail=str(exc),
        ) from exc

    return map_validate_result(result, telemetry)
