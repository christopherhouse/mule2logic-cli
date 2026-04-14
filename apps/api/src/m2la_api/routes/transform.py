"""Transform route — converts a MuleSoft project or single flow to Logic Apps artifacts.

The endpoint accepts ``multipart/form-data`` with an uploaded project zip
(for project mode) or a single-flow XML file.  The uploaded content is
extracted to a server-side temporary directory, processed through the
full 5-agent pipeline, and the temp directory is cleaned up afterward.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from m2la_agents import MigrationOrchestrator
from m2la_contracts import (
    InputMode,
    TelemetryContext,
    TransformResponse,
)

from m2la_api.dependencies import get_chat_client
from m2la_api.models.errors import ApiError
from m2la_api.services.result_mapper import map_transform_result
from m2la_api.services.upload_handler import (
    UploadError,
    cleanup_upload,
    extract_project_upload,
    save_single_flow_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/transform", response_model=TransformResponse)
async def transform(
    file: UploadFile = File(..., description="Project zip archive or single-flow XML file"),
    mode: str | None = Form(None, description="Input mode: 'project' or 'single_flow'. Auto-detected if omitted."),
    output_directory: str | None = Form(None, description="Logical output directory name (default: ./output)"),
    telemetry_json: str | None = Form(None, description="Telemetry context as JSON string"),
    chat_client: Any = Depends(get_chat_client),
) -> TransformResponse:
    """Transform a MuleSoft project or single flow XML into Logic Apps artifacts.

    Upload a project zip archive for project mode, or a single ``.xml``
    file for single-flow mode.  The server extracts the upload, runs the
    full 5-agent pipeline (Analyzer → Planner → Transformer → Validator →
    RepairAdvisor), and returns the transformation results.
    """
    resolved_mode = _resolve_mode(mode, file.filename)
    output_dir = output_directory or "./output"
    telemetry = _parse_telemetry(telemetry_json)

    input_path: Path | None = None
    try:
        input_path = await _extract_upload(file, resolved_mode)

        orchestrator = MigrationOrchestrator(
            client=chat_client,
            include_repair=True,
        )

        result = await asyncio.to_thread(
            orchestrator.run,
            str(input_path),
            input_mode=resolved_mode,
            output_directory=output_dir,
            correlation_id=telemetry.correlation_id,
            trace_id=telemetry.trace_id,
            span_id=telemetry.span_id,
        )

        return map_transform_result(result, resolved_mode, output_dir, telemetry)

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
        logger.exception("Transform pipeline failed")
        raise ApiError(
            status_code=503,
            error_code="PIPELINE_ERROR",
            message="Transform pipeline failed",
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
