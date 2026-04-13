"""Tests for the analyze endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from m2la_api.main import app


@pytest.fixture
def transport() -> ASGITransport:
    return ASGITransport(app=app)


class TestAnalyzeEndpoint:
    """Tests for POST /analyze."""

    @pytest.mark.asyncio
    async def test_project_mode_auto_detect(self, transport: ASGITransport) -> None:
        """Directory path should auto-detect as project mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/analyze", json={"input_path": "/tmp/mulesoft-project"})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "project"
        assert data["project_name"] == "placeholder-project"
        assert data["flows"] == []
        assert "telemetry" in data
        assert "trace_id" in data["telemetry"]

    @pytest.mark.asyncio
    async def test_single_flow_mode_auto_detect(self, transport: ASGITransport) -> None:
        """XML file path should auto-detect as single-flow mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/analyze", json={"input_path": "/tmp/flows/main.xml"})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "single_flow"
        assert data["project_name"] is None

    @pytest.mark.asyncio
    async def test_explicit_mode_override(self, transport: ASGITransport) -> None:
        """Explicit mode parameter should override auto-detection."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                json={"input_path": "/tmp/mulesoft-project", "mode": "single_flow"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "single_flow"

    @pytest.mark.asyncio
    async def test_telemetry_propagated(self, transport: ASGITransport) -> None:
        """Provided telemetry context should be returned in response."""
        telemetry = {
            "trace_id": "abc123",
            "span_id": "span01",
            "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
        }
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                json={"input_path": "/tmp/project", "telemetry": telemetry},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["telemetry"]["trace_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_missing_input_path_returns_422(self, transport: ASGITransport) -> None:
        """Missing input_path should return 422 validation error."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/analyze", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_shape(self, transport: ASGITransport) -> None:
        """Response should contain all expected AnalyzeResponse fields."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/analyze", json={"input_path": "/tmp/project"})
        data = response.json()
        expected_keys = {"mode", "project_name", "flows", "overall_constructs", "gaps", "warnings", "telemetry"}
        assert expected_keys.issubset(data.keys())
