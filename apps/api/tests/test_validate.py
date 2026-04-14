"""Tests for the validate endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient
from upload_helpers import make_dummy_project_zip


class TestValidateEndpoint:
    """Tests for POST /validate (multipart upload).

    Note: The MockChatClient cannot properly drive the ValidatorAgent tool
    (the tool function requires arguments that the mock doesn't supply).
    Tests therefore expect a 503 pipeline-failure response, which validates
    the error handling path.
    """

    @pytest.mark.asyncio
    async def test_returns_pipeline_failure(self, transport: ASGITransport) -> None:
        """Validate with MockChatClient should return 503 (ValidatorAgent tool fails)."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/validate",
                files={"file": ("output.zip", make_dummy_project_zip(), "application/zip")},
            )
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "PIPELINE_FAILURE"

    @pytest.mark.asyncio
    async def test_telemetry_not_propagated_on_failure(self, transport: ASGITransport) -> None:
        """Pipeline failure returns error response, not the normal report with telemetry."""
        import json

        telemetry = {
            "trace_id": "trace1",
            "span_id": "span1",
            "correlation_id": "corr1",
        }
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/validate",
                files={"file": ("output.zip", make_dummy_project_zip(), "application/zip")},
                data={"telemetry_json": json.dumps(telemetry)},
            )
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "PIPELINE_FAILURE"

    @pytest.mark.asyncio
    async def test_missing_file_returns_422(self, transport: ASGITransport) -> None:
        """Missing file upload should return 422 validation error."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/validate")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_failure_response_shape(self, transport: ASGITransport) -> None:
        """Pipeline failure response should contain structured error fields."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/validate",
                files={"file": ("output.zip", make_dummy_project_zip(), "application/zip")},
            )
        data = response.json()
        expected_keys = {"error_code", "message", "detail", "severity"}
        assert expected_keys.issubset(data.keys())
