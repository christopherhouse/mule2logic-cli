"""Tests for structured error handling."""

import pytest
from httpx import ASGITransport, AsyncClient

from m2la_api.main import app
from m2la_api.models.errors import ApiError, ErrorResponse


@pytest.fixture
def transport() -> ASGITransport:
    return ASGITransport(app=app)


class TestErrorResponse:
    """Tests for the ErrorResponse model."""

    def test_error_response_defaults(self) -> None:
        err = ErrorResponse(error_code="TEST_001", message="Something went wrong")
        assert err.error_code == "TEST_001"
        assert err.message == "Something went wrong"
        assert err.detail is None
        assert err.severity == "error"

    def test_error_response_with_detail(self) -> None:
        err = ErrorResponse(
            error_code="TEST_002",
            message="Bad request",
            detail="Missing field X",
            severity="warning",
        )
        assert err.detail == "Missing field X"
        assert err.severity == "warning"


class TestApiError:
    """Tests for the ApiError exception class."""

    def test_api_error_attributes(self) -> None:
        exc = ApiError(status_code=404, error_code="NOT_FOUND", message="Resource not found")
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"
        assert exc.message == "Resource not found"
        assert str(exc) == "Resource not found"


class TestErrorHandler:
    """Tests for the exception handler integration."""

    @pytest.mark.asyncio
    async def test_api_error_returns_structured_response(self, transport: ASGITransport) -> None:
        """ApiError raised in a route should be caught and returned as ErrorResponse JSON."""

        # Temporarily add a route that raises ApiError
        @app.get("/test-error")
        async def _raise_error() -> None:
            raise ApiError(
                status_code=400,
                error_code="TEST_ERR",
                message="Test error",
                detail="Extra detail",
            )

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test-error")

        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "TEST_ERR"
        assert data["message"] == "Test error"
        assert data["detail"] == "Extra detail"
        assert data["severity"] == "error"

        # Clean up the test route
        app.routes[:] = [r for r in app.routes if getattr(r, "path", None) != "/test-error"]
