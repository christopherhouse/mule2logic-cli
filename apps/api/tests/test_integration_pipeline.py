"""Integration tests — full pipeline roundtrip through MockChatClient.

These tests exercise the real agent pipeline (via ``MigrationOrchestrator``)
with a ``MockChatClient`` that simulates LLM tool-calling.  They verify that
``/analyze``, ``/transform``, and ``/validate`` return contract-conforming
responses when uploading real sample projects as zip archives.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from upload_helpers import make_project_zip

_SAMPLE_DIR = Path(__file__).resolve().parents[3] / "packages" / "sample-projects"
_HELLO_WORLD = _SAMPLE_DIR / "hello-world-project"
_STANDALONE_FLOW = _SAMPLE_DIR / "standalone-flow.xml"


class TestIntegrationAnalyze:
    """Integration tests for POST /analyze through the agent pipeline."""

    @pytest.mark.asyncio
    async def test_analyze_project_mode(self, transport: ASGITransport) -> None:
        """Analyze the hello-world sample project in project mode."""
        project_zip = make_project_zip(_HELLO_WORLD)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/analyze",
                files={"file": ("hello-world-project.zip", project_zip, "application/zip")},
                data={"mode": "project"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "project"
        assert "flows" in data
        assert "overall_constructs" in data
        assert "gaps" in data
        assert "warnings" in data
        assert "telemetry" in data

    @pytest.mark.asyncio
    async def test_analyze_single_flow_mode(self, transport: ASGITransport) -> None:
        """Analyze the standalone flow XML in single-flow mode."""
        flow_content = _STANDALONE_FLOW.read_bytes()
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/analyze",
                files={"file": ("standalone-flow.xml", flow_content, "application/xml")},
                data={"mode": "single_flow"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "single_flow"
        assert data["project_name"] is None
        assert "overall_constructs" in data

    @pytest.mark.asyncio
    async def test_analyze_includes_reasoning(self, transport: ASGITransport) -> None:
        """Analyze response should include agent reasoning in warnings."""
        project_zip = make_project_zip(_HELLO_WORLD)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/analyze",
                files={"file": ("hello-world-project.zip", project_zip, "application/zip")},
                data={"mode": "project"},
            )
        assert resp.status_code == 200
        data = resp.json()
        agent_warnings = [w for w in data["warnings"] if w["code"] == "AGENT_REASONING"]
        assert len(agent_warnings) > 0, "Expected at least one agent reasoning warning"


class TestIntegrationTransform:
    """Integration tests for POST /transform through the full 5-agent pipeline."""

    @pytest.mark.asyncio
    async def test_transform_project_mode(self, transport: ASGITransport) -> None:
        """Transform the hello-world project through the full pipeline."""
        project_zip = make_project_zip(_HELLO_WORLD)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/transform",
                files={"file": ("hello-world-project.zip", project_zip, "application/zip")},
                data={"mode": "project", "output_directory": "/tmp/test-output"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "project"
        assert data["artifacts"]["output_directory"] == "/tmp/test-output"
        assert data["artifacts"]["mode"] == "project"
        assert "constructs" in data
        assert "warnings" in data

    @pytest.mark.asyncio
    async def test_transform_single_flow_mode(self, transport: ASGITransport) -> None:
        """Transform the standalone flow through the full pipeline."""
        flow_content = _STANDALONE_FLOW.read_bytes()
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/transform",
                files={"file": ("standalone-flow.xml", flow_content, "application/xml")},
                data={"mode": "single_flow"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "single_flow"
        assert data["project_name"] is None
        assert data["artifacts"]["mode"] == "single_flow"

    @pytest.mark.asyncio
    async def test_transform_response_shape(self, transport: ASGITransport) -> None:
        """Transform response should have all expected fields."""
        project_zip = make_project_zip(_HELLO_WORLD)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/transform",
                files={"file": ("hello-world-project.zip", project_zip, "application/zip")},
                data={"mode": "project"},
            )
        data = resp.json()
        expected = {"mode", "project_name", "artifacts", "gaps", "warnings", "constructs", "telemetry"}
        assert expected.issubset(data.keys())


class TestIntegrationValidate:
    """Integration tests for POST /validate through ValidatorAgent."""

    @pytest.mark.asyncio
    async def test_validate_returns_report(self, transport: ASGITransport) -> None:
        """Validate endpoint should return a validation report."""
        project_zip = make_project_zip(_HELLO_WORLD)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/validate",
                files={"file": ("output.zip", project_zip, "application/zip")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "valid" in data
        assert "issues" in data
        assert "artifacts_validated" in data
        assert "telemetry" in data

    @pytest.mark.asyncio
    async def test_validate_response_shape(self, transport: ASGITransport) -> None:
        """Validate response should have all expected fields."""
        project_zip = make_project_zip(_HELLO_WORLD)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/validate",
                files={"file": ("output.zip", project_zip, "application/zip")},
            )
        data = resp.json()
        expected = {"valid", "issues", "artifacts_validated", "telemetry"}
        assert expected.issubset(data.keys())
