"""Analyze route — accepts a MuleSoft project or single flow for analysis.

The endpoint accepts ``multipart/form-data`` with an uploaded project zip
(for project mode) or a single-flow XML file.  The uploaded content is
extracted to a server-side temporary directory, processed through the
agent pipeline, and the temp directory is cleaned up afterward.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from m2la_agents import AnalyzerAgent, MigrationOrchestrator, PlannerAgent
from m2la_contracts import (
    AnalyzeResponse,
    InputMode,
    TelemetryContext,
)

from m2la_api.dependencies import get_chat_client
from m2la_api.models.errors import ApiError
from m2la_api.services.result_mapper import map_analyze_result
from m2la_api.services.upload_handler import (
    UploadError,
    cleanup_upload,
    extract_project_upload,
    save_single_flow_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(..., description="Project zip archive or single-flow XML file"),
    mode: str | None = Form(None, description="Input mode: 'project' or 'single_flow'. Auto-detected if omitted."),
    telemetry_json: str | None = Form(None, description="Telemetry context as JSON string"),
    chat_client: Any = Depends(get_chat_client),
) -> AnalyzeResponse:
    """Analyze a MuleSoft project or single flow XML.

    Upload a project zip archive for project mode, or a single ``.xml``
    file for single-flow mode.  The server extracts the upload, runs the
    AnalyzerAgent + PlannerAgent pipeline, and returns the analysis.
    """
    # Resolve input mode
    resolved_mode = _resolve_mode(mode, file.filename)

    telemetry = _parse_telemetry(telemetry_json)

    # Extract upload to temp directory
    input_path: Path | None = None
    try:
        input_path = await _extract_upload(file, resolved_mode)

        orchestrator = MigrationOrchestrator(
            client=chat_client,
            agents=[AnalyzerAgent(), PlannerAgent()],
            include_repair=False,
        )

        result = await asyncio.to_thread(
            orchestrator.run,
            str(input_path),
            input_mode=resolved_mode,
            correlation_id=telemetry.correlation_id,
            trace_id=telemetry.trace_id,
            span_id=telemetry.span_id,
        )

        return map_analyze_result(result, resolved_mode, telemetry)

    except UploadError as exc:
        raise ApiError(
            status_code=400,
            error_code="UPLOAD_ERROR",
            message="Failed to process uploaded file",
            detail=str(exc),
        ) from exc
    except ApiError:
        raise
    except Exception as exc:
        logger.exception("Analyze pipeline failed")
        raise ApiError(
            status_code=503,
            error_code="PIPELINE_ERROR",
            message="Analysis pipeline failed",
            detail=str(exc),
        ) from exc
    finally:
        if input_path is not None:
            cleanup_upload(input_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_mode(mode: str | None, filename: str | None) -> InputMode:
    """Resolve the input mode from the form field or filename."""
    if mode is not None:
        return InputMode(mode)
    # Auto-detect from filename
    if filename and filename.lower().endswith(".xml"):
        return InputMode.SINGLE_FLOW
    return InputMode.PROJECT


def _parse_telemetry(telemetry_json: str | None) -> TelemetryContext:
    """Parse a telemetry JSON string or generate defaults."""
    if telemetry_json:
        data = json.loads(telemetry_json)
        return TelemetryContext(**data)
    return TelemetryContext(
        trace_id=uuid.uuid4().hex[:16],
        span_id=uuid.uuid4().hex[:8],
        correlation_id=str(uuid.uuid4()),
    )


async def _extract_upload(file: UploadFile, mode: InputMode) -> Path:
    """Extract the uploaded file based on the resolved mode."""
    if mode == InputMode.SINGLE_FLOW:
        return await save_single_flow_upload(file)
    return await extract_project_upload(file)
