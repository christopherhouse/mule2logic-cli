"""Tests for the analyze endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient
from upload_helpers import make_dummy_project_zip, make_single_flow_xml


class TestAnalyzeEndpoint:
    """Tests for POST /analyze (multipart upload)."""

    @pytest.mark.asyncio
    async def test_project_mode_explicit(self, transport: ASGITransport) -> None:
        """Uploading a zip with mode=project should return project mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "project"
        assert "telemetry" in data
        assert "trace_id" in data["telemetry"]

    @pytest.mark.asyncio
    async def test_single_flow_mode_explicit(self, transport: ASGITransport) -> None:
        """Uploading XML with mode=single_flow should return single-flow mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                files={"file": ("flow.xml", make_single_flow_xml(), "application/xml")},
                data={"mode": "single_flow"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "single_flow"
        assert data["project_name"] is None

    @pytest.mark.asyncio
    async def test_mode_auto_detected_from_filename(self, transport: ASGITransport) -> None:
        """Mode should be auto-detected from the uploaded filename."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                files={"file": ("main.xml", make_single_flow_xml(), "application/xml")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "single_flow"

    @pytest.mark.asyncio
    async def test_telemetry_propagated(self, transport: ASGITransport) -> None:
        """Provided telemetry context should be returned in response."""
        import json

        telemetry = {
            "trace_id": "abc123",
            "span_id": "span01",
            "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
        }
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project", "telemetry_json": json.dumps(telemetry)},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["telemetry"]["trace_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_missing_file_returns_422(self, transport: ASGITransport) -> None:
        """Missing file upload should return 422 validation error."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/analyze")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_shape(self, transport: ASGITransport) -> None:
        """Response should contain all expected AnalyzeResponse fields."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/analyze",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project"},
            )
        data = response.json()
        expected_keys = {"mode", "project_name", "flows", "overall_constructs", "gaps", "warnings", "telemetry"}
        assert expected_keys.issubset(data.keys())
