"""Tests for the validate endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient


class TestValidateEndpoint:
    """Tests for POST /validate."""

    @pytest.mark.asyncio
    async def test_valid_request(self, transport: ASGITransport) -> None:
        """Valid request should return a validation report."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/validate", json={"output_directory": "/tmp/output"})
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "issues" in data
        assert "artifacts_validated" in data
        assert "telemetry" in data

    @pytest.mark.asyncio
    async def test_telemetry_propagated(self, transport: ASGITransport) -> None:
        """Provided telemetry context should be returned in response."""
        telemetry = {
            "trace_id": "trace1",
            "span_id": "span1",
            "correlation_id": "corr1",
        }
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/validate",
                json={"output_directory": "/tmp/output", "telemetry": telemetry},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["telemetry"]["trace_id"] == "trace1"

    @pytest.mark.asyncio
    async def test_missing_output_directory_returns_422(self, transport: ASGITransport) -> None:
        """Missing output_directory should return 422 validation error."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/validate", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_shape(self, transport: ASGITransport) -> None:
        """Response should contain all expected ValidationReport fields."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/validate", json={"output_directory": "/tmp/output"})
        data = response.json()
        expected_keys = {"valid", "issues", "artifacts_validated", "telemetry"}
        assert expected_keys.issubset(data.keys())
