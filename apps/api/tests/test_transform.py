"""Tests for the transform endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient
from upload_helpers import make_dummy_project_zip, make_single_flow_xml


class TestTransformEndpoint:
    """Tests for POST /transform (multipart upload)."""

    @pytest.mark.asyncio
    async def test_project_mode_explicit(self, transport: ASGITransport) -> None:
        """Uploading a zip with mode=project should return project mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/transform",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "project"
        assert data["artifacts"]["mode"] == "project"

    @pytest.mark.asyncio
    async def test_single_flow_mode_explicit(self, transport: ASGITransport) -> None:
        """Uploading XML with mode=single_flow should return single-flow mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/transform",
                files={"file": ("flow.xml", make_single_flow_xml(), "application/xml")},
                data={"mode": "single_flow"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "single_flow"
        assert data["project_name"] is None
        assert data["artifacts"]["mode"] == "single_flow"

    @pytest.mark.asyncio
    async def test_custom_output_directory(self, transport: ASGITransport) -> None:
        """Custom output_directory should be reflected in the artifact manifest."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/transform",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project", "output_directory": "/custom/output"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["artifacts"]["output_directory"] == "/custom/output"

    @pytest.mark.asyncio
    async def test_default_output_directory(self, transport: ASGITransport) -> None:
        """Default output directory should be ./output when not specified."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/transform",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["artifacts"]["output_directory"] == "./output"

    @pytest.mark.asyncio
    async def test_missing_file_returns_422(self, transport: ASGITransport) -> None:
        """Missing file upload should return 422 validation error."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/transform")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_shape(self, transport: ASGITransport) -> None:
        """Response should contain all expected TransformResponse fields."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/transform",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project"},
            )
        data = response.json()
        expected_keys = {"mode", "project_name", "artifacts", "gaps", "warnings", "constructs", "telemetry"}
        assert expected_keys.issubset(data.keys())
