"""Validate route — validates generated Logic Apps artifacts.

The endpoint accepts ``multipart/form-data`` with a zip archive containing
the generated Logic Apps output artifacts.  The uploaded content is
extracted to a server-side temporary directory, validated through the
ValidatorAgent pipeline, and the temp directory is cleaned up afterward.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from m2la_agents import MigrationOrchestrator, ValidatorAgent
from m2la_contracts import InputMode, ValidationReport

from m2la_api.dependencies import get_chat_client
from m2la_api.models.errors import ApiError
from m2la_api.routes.route_utils import check_pipeline_failure, parse_telemetry
from m2la_api.services.result_mapper import map_validate_result
from m2la_api.services.upload_handler import UploadError, cleanup_upload, extract_project_upload

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/validate", response_model=ValidationReport)
async def validate(
    file: UploadFile = File(..., description="Zip archive of generated Logic Apps output artifacts"),
    telemetry_json: str | None = Form(None, description="Telemetry context as JSON string"),
    chat_client: Any = Depends(get_chat_client),
) -> ValidationReport:
    """Validate generated Logic Apps artifacts.

    Upload a zip archive containing the generated output directory.
    The server extracts the upload, runs the ValidatorAgent pipeline,
    and returns a validation report.
    """
    telemetry = parse_telemetry(telemetry_json)

    output_path: Path | None = None
    try:
        output_path = await extract_project_upload(file)

        orchestrator = MigrationOrchestrator(
            client=chat_client,
            agents=[ValidatorAgent()],
            include_repair=False,
        )

        result = await asyncio.to_thread(
            orchestrator.run,
            str(output_path),
            input_mode=InputMode.PROJECT,
            correlation_id=telemetry.correlation_id,
            trace_id=telemetry.trace_id,
            span_id=telemetry.span_id,
        )

        check_pipeline_failure(result, "Validation")

        return map_validate_result(result, telemetry)

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
        logger.exception("Validate pipeline failed")
        raise ApiError(
            status_code=503,
            error_code="PIPELINE_ERROR",
            message="Validation pipeline failed",
            detail=str(exc),
        ) from exc
    finally:
        if output_path is not None:
            cleanup_upload(output_path)
