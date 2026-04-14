"""Shared route utilities for the upload-based API endpoints.

Consolidates common helpers used across analyze, transform, and validate
routes: telemetry parsing, mode resolution, upload extraction, and
pipeline failure detection.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from m2la_agents.models import AgentStatus, OrchestrationResult
from m2la_contracts import InputMode, TelemetryContext

from m2la_api.models.errors import ApiError
from m2la_api.services.upload_handler import (
    extract_project_upload,
    save_single_flow_upload,
)

logger = logging.getLogger(__name__)


def resolve_mode(mode: str | None, filename: str | None) -> InputMode:
    """Resolve the input mode from the form field or filename.

    Raises:
        ValueError: If *mode* is not a valid ``InputMode`` value.
    """
    if mode is not None:
        try:
            return InputMode(mode)
        except ValueError as exc:
            raise ValueError(f"Invalid mode '{mode}'. Must be 'project' or 'single_flow'.") from exc
    # Auto-detect from filename
    if filename and filename.lower().endswith(".xml"):
        return InputMode.SINGLE_FLOW
    return InputMode.PROJECT


def parse_telemetry(telemetry_json: str | None) -> TelemetryContext:
    """Parse a telemetry JSON string or generate defaults."""
    if telemetry_json:
        data = json.loads(telemetry_json)
        return TelemetryContext(**data)
    return TelemetryContext(
        trace_id=uuid.uuid4().hex[:16],
        span_id=uuid.uuid4().hex[:8],
        correlation_id=str(uuid.uuid4()),
    )


async def extract_upload(file: object, mode: InputMode) -> Path:
    """Extract the uploaded file based on the resolved mode.

    Args:
        file: A FastAPI ``UploadFile`` instance.
        mode: The resolved input mode.

    Returns:
        Path to the extracted project root or saved XML file.
    """
    if mode == InputMode.SINGLE_FLOW:
        return await save_single_flow_upload(file)  # type: ignore[arg-type]
    return await extract_project_upload(file)  # type: ignore[arg-type]


def check_pipeline_failure(result: OrchestrationResult, pipeline_name: str) -> None:
    """Raise :class:`ApiError` if the pipeline overall status is FAILURE.

    Args:
        result: The orchestration result to check.
        pipeline_name: Human-readable name of the pipeline (e.g. "Analysis").

    Raises:
        ApiError: 503 with ``PIPELINE_FAILURE`` error code.
    """
    if result.overall_status == AgentStatus.FAILURE:
        detail = (
            str(result.final_output)
            if result.final_output
            else f"{pipeline_name} orchestration completed with FAILURE status"
        )
        logger.error("%s pipeline returned failure status", pipeline_name)
        raise ApiError(
            status_code=503,
            error_code="PIPELINE_FAILURE",
            message=f"{pipeline_name} pipeline failed",
            detail=detail,
        )
