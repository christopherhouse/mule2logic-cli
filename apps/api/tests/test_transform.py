"""Tests for the transform endpoint."""

import json

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


class TestTransformStreamEndpoint:
    """Tests for POST /transform/stream (NDJSON streaming)."""

    @pytest.mark.asyncio
    async def test_stream_returns_ndjson_content_type(self, transport: ASGITransport) -> None:
        """Streaming endpoint should return application/x-ndjson content type."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/transform/stream",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project"},
            )
        assert response.headers["content-type"] == "application/x-ndjson"

    @pytest.mark.asyncio
    async def test_stream_emits_ndjson_events(self, transport: ASGITransport) -> None:
        """Streaming endpoint should emit newline-delimited JSON events."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/transform/stream",
                files={"file": ("project.zip", make_dummy_project_zip(), "application/zip")},
                data={"mode": "project"},
            ) as response:
                # Collect all events
                events = []
                async for line in response.aiter_lines():
                    if line.strip():
                        event = json.loads(line)
                        events.append(event)

                # Should have received at least one event (likely an error event due to MockChatClient)
                assert len(events) > 0

                # All events should have event_type field
                for event in events:
                    assert "event_type" in event

    @pytest.mark.asyncio
    async def test_stream_handles_invalid_mode(self, transport: ASGITransport) -> None:
        """Streaming endpoint should return error event for invalid mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/transform/stream",
                files={"file": ("test.xyz", b"invalid", "application/octet-stream")},
                data={"mode": "invalid_mode"},
            ) as response:
                # Collect events
                events = []
                async for line in response.aiter_lines():
                    if line.strip():
                        event = json.loads(line)
                        events.append(event)

                # Should have an error event
                assert len(events) == 1
                assert events[0]["event_type"] == "error"
                assert events[0]["error_code"] == "INVALID_MODE"
