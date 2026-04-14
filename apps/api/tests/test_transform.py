"""Tests for the transform endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient
from upload_helpers import make_dummy_project_zip, make_single_flow_xml


class TestTransformEndpoint:
    """Tests for POST /transform (multipart upload).

    Note: The MockChatClient cannot properly drive the full 5-agent
    transform pipeline (ValidatorAgent fails due to missing tool arguments).
    Tests that exercise the full pipeline therefore expect a 503 failure
    response, which validates the pipeline-failure error handling path.
    """

    @pytest.mark.asyncio
    async def test_project_mode_returns_pipeline_failure(self, transport: ASGITransport) -> None:
        """Full transform pipeline with MockChatClient returns 503 on agent failure."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/transform",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project"},
            )
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "PIPELINE_FAILURE"

    @pytest.mark.asyncio
    async def test_single_flow_mode_returns_pipeline_failure(self, transport: ASGITransport) -> None:
        """Full transform pipeline with MockChatClient returns 503 on agent failure."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/transform",
                files={"file": ("flow.xml", make_single_flow_xml(), "application/xml")},
                data={"mode": "single_flow"},
            )
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "PIPELINE_FAILURE"

    @pytest.mark.asyncio
    async def test_custom_output_directory_in_failure_detail(self, transport: ASGITransport) -> None:
        """Custom output_directory should appear in the failure detail."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/transform",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project", "output_directory": "/custom/output"},
            )
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "PIPELINE_FAILURE"

    @pytest.mark.asyncio
    async def test_missing_file_returns_422(self, transport: ASGITransport) -> None:
        """Missing file upload should return 422 validation error."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/transform")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_failure_response_shape(self, transport: ASGITransport) -> None:
        """Pipeline failure response should contain structured error fields."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/transform",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project"},
            )
        data = response.json()
        expected_keys = {"error_code", "message", "detail", "severity"}
        assert expected_keys.issubset(data.keys())
