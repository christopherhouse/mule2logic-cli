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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from m2la_agents import MigrationOrchestrator, StreamingEvent, StreamingEventType
from m2la_contracts import TransformResponse

from m2la_api.dependencies import get_chat_client
from m2la_api.models.errors import ApiError
from m2la_api.routes.route_utils import check_pipeline_failure, extract_upload, parse_telemetry, resolve_mode
from m2la_api.services.result_mapper import map_transform_result
from m2la_api.services.upload_handler import UploadError, cleanup_upload

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
    try:
        resolved_mode = resolve_mode(mode, file.filename)
    except ValueError as exc:
        raise ApiError(status_code=400, error_code="INVALID_MODE", message=str(exc)) from exc

    output_dir = output_directory or "./output"
    telemetry = parse_telemetry(telemetry_json)

    input_path: Path | None = None
    try:
        input_path = await extract_upload(file, resolved_mode)

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

        check_pipeline_failure(result, "Transform")

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


@router.post("/transform/stream")
async def transform_stream(
    file: UploadFile = File(..., description="Project zip archive or single-flow XML file"),
    mode: str | None = Form(None, description="Input mode: 'project' or 'single_flow'. Auto-detected if omitted."),
    output_directory: str | None = Form(None, description="Logical output directory name (default: ./output)"),
    telemetry_json: str | None = Form(None, description="Telemetry context as JSON string"),
    chat_client: Any = Depends(get_chat_client),
) -> StreamingResponse:
    """Transform with HTTP streaming.

    Returns real-time progress updates as the migration pipeline executes,
    allowing clients to display agent-by-agent progress instead of waiting
    for the entire pipeline to complete.

    The response uses HTTP chunked transfer encoding with newline-delimited JSON (NDJSON).
    Each line is a complete JSON object representing an event.

    Example NDJSON stream::

        {"event_type": "agent_started", "agent_name": "AnalyzerAgent", "correlation_id": "...", ...}
        {"event_type": "agent_completed", "agent_name": "AnalyzerAgent", "status": "success", ...}
        {"event_type": "complete", "overall_status": "success", "total_duration_ms": 5678, ...}

    Args:
        file: Project zip or single flow XML file
        mode: Input mode override
        output_directory: Output directory for artifacts
        telemetry_json: Telemetry context JSON
        chat_client: Injected chat client dependency

    Returns:
        StreamingResponse with application/x-ndjson content
    """
    try:
        resolved_mode = resolve_mode(mode, file.filename)
    except ValueError as exc:
        error_msg = str(exc)

        # Return error as NDJSON event using the standard StreamingEvent envelope
        async def error_stream():
            yield _format_ndjson_event(
                "error",
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "correlation_id": None,
                    "agent_name": None,
                    "message": error_msg,
                    "data": {"error_code": "INVALID_MODE"},
                },
            )

        return StreamingResponse(error_stream(), media_type="application/x-ndjson")

    output_dir = output_directory or "./output"
    telemetry = parse_telemetry(telemetry_json)

    async def event_generator():
        input_path: Path | None = None
        orchestrator_error_emitted = False
        try:
            input_path = await extract_upload(file, resolved_mode)

            orchestrator = MigrationOrchestrator(
                client=chat_client,
                include_repair=True,
            )

            async for event in orchestrator.run_streaming(
                str(input_path),
                input_mode=resolved_mode,
                output_directory=output_dir,
                correlation_id=telemetry.correlation_id,
                trace_id=telemetry.trace_id,
                span_id=telemetry.span_id,
            ):
                if event.event_type == StreamingEventType.ERROR:
                    orchestrator_error_emitted = True
                yield _format_ndjson_event(event.event_type.value, _serialize_streaming_event(event))

        except UploadError as exc:
            logger.exception("Upload failed during streaming transform")
            yield _format_ndjson_event(
                "error",
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "correlation_id": None,
                    "agent_name": None,
                    "message": "Failed to process uploaded file",
                    "data": {"error_code": "UPLOAD_ERROR", "detail": str(exc)},
                },
            )
        except Exception as exc:
            if not orchestrator_error_emitted:
                logger.exception("Transform pipeline failed during streaming")
                yield _format_ndjson_event(
                    "error",
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "correlation_id": None,
                        "agent_name": None,
                        "message": "Transform pipeline failed",
                        "data": {"error_code": "PIPELINE_ERROR", "detail": str(exc)},
                    },
                )
            else:
                logger.debug("Suppressing duplicate error event — orchestrator already emitted one")
        finally:
            if input_path is not None:
                cleanup_upload(input_path)

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


def _format_ndjson_event(event_type: str, data: dict[str, Any]) -> str:
    """Format a newline-delimited JSON event.

    NDJSON format: each event is a single JSON object on one line, followed by a newline.

    Args:
        event_type: Event type name
        data: Event payload (will be merged with event_type)

    Returns:
        Formatted NDJSON event string (JSON + newline)
    """
    event_data = {"event_type": event_type, **data}
    return json.dumps(event_data, default=str) + "\n"


def _serialize_streaming_event(event: StreamingEvent) -> dict[str, Any]:
    """Convert StreamingEvent to JSON-serializable dict.

    Note: ``event_type`` is intentionally omitted here — it is injected by
    ``_format_ndjson_event`` to avoid duplication.

    Args:
        event: StreamingEvent from orchestrator

    Returns:
        JSON-serializable dictionary (without event_type)
    """
    return {
        "timestamp": event.timestamp.isoformat(),
        "correlation_id": event.correlation_id,
        "agent_name": event.agent_name,
        "message": event.message,
        "data": event.data,
    }
