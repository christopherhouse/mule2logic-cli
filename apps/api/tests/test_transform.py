"""Tests for the transform endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from m2la_api.main import app


@pytest.fixture
def transport() -> ASGITransport:
    return ASGITransport(app=app)


class TestTransformEndpoint:
    """Tests for POST /transform."""

    @pytest.mark.asyncio
    async def test_project_mode_auto_detect(self, transport: ASGITransport) -> None:
        """Directory path should auto-detect as project mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/transform", json={"input_path": "/tmp/mulesoft-project"})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "project"
        assert data["project_name"] == "placeholder-project"
        assert data["artifacts"]["artifacts"] == []
        assert data["artifacts"]["mode"] == "project"

    @pytest.mark.asyncio
    async def test_single_flow_mode_auto_detect(self, transport: ASGITransport) -> None:
        """XML file path should auto-detect as single-flow mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/transform", json={"input_path": "/tmp/flows/main.xml"})
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
                json={"input_path": "/tmp/project", "output_directory": "/custom/output"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["artifacts"]["output_directory"] == "/custom/output"

    @pytest.mark.asyncio
    async def test_default_output_directory(self, transport: ASGITransport) -> None:
        """Default output directory should be ./output when not specified."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/transform", json={"input_path": "/tmp/project"})
        assert response.status_code == 200
        data = response.json()
        assert data["artifacts"]["output_directory"] == "./output"

    @pytest.mark.asyncio
    async def test_missing_input_path_returns_422(self, transport: ASGITransport) -> None:
        """Missing input_path should return 422 validation error."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/transform", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_shape(self, transport: ASGITransport) -> None:
        """Response should contain all expected TransformResponse fields."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/transform", json={"input_path": "/tmp/project"})
        data = response.json()
        expected_keys = {"mode", "project_name", "artifacts", "gaps", "warnings", "constructs", "telemetry"}
        assert expected_keys.issubset(data.keys())
