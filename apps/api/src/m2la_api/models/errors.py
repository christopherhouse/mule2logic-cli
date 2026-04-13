"""Structured error models and exception handling."""

from fastapi import Request
from fastapi.responses import JSONResponse
from m2la_contracts.enums import Severity
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Structured error response returned by the API."""

    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    detail: str | None = Field(default=None, description="Optional additional detail")
    severity: Severity = Field(default=Severity.ERROR, description="Error severity")


class ApiError(Exception):
    """Application-level error that maps to a structured HTTP response."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        detail: str | None = None,
        severity: Severity = Severity.ERROR,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.detail = detail
        self.severity = severity
        super().__init__(message)


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    """FastAPI exception handler that converts ApiError to ErrorResponse JSON."""
    body = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        detail=exc.detail,
        severity=exc.severity,
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())
