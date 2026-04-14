"""Integration tests — full pipeline roundtrip through MockChatClient.

These tests exercise the real agent pipeline (via ``MigrationOrchestrator``)
with a ``MockChatClient`` that simulates LLM tool-calling.  They verify that
``/analyze``, ``/transform``, and ``/validate`` return contract-conforming
responses when pointed at sample projects.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

_SAMPLE_DIR = Path(__file__).resolve().parents[3] / "packages" / "sample-projects"
_HELLO_WORLD = str(_SAMPLE_DIR / "hello-world-project")
_STANDALONE_FLOW = str(_SAMPLE_DIR / "standalone-flow.xml")


class TestIntegrationAnalyze:
    """Integration tests for POST /analyze through the agent pipeline."""

    @pytest.mark.asyncio
    async def test_analyze_project_mode(self, transport: ASGITransport) -> None:
        """Analyze the hello-world sample project in project mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/analyze", json={"input_path": _HELLO_WORLD})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "project"
        # Should have response shape
        assert "flows" in data
        assert "overall_constructs" in data
        assert "gaps" in data
        assert "warnings" in data
        assert "telemetry" in data

    @pytest.mark.asyncio
    async def test_analyze_single_flow_mode(self, transport: ASGITransport) -> None:
        """Analyze the standalone flow XML in single-flow mode."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/analyze", json={"input_path": _STANDALONE_FLOW})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "single_flow"
        assert data["project_name"] is None
        assert "overall_constructs" in data

    @pytest.mark.asyncio
    async def test_analyze_includes_reasoning(self, transport: ASGITransport) -> None:
        """Analyze response should include agent reasoning in warnings."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/analyze", json={"input_path": _HELLO_WORLD})
        assert resp.status_code == 200
        data = resp.json()
        # Reasoning summaries are surfaced as AGENT_REASONING warnings
        agent_warnings = [w for w in data["warnings"] if w["code"] == "AGENT_REASONING"]
        assert len(agent_warnings) > 0, "Expected at least one agent reasoning warning"


class TestIntegrationTransform:
    """Integration tests for POST /transform through the full 5-agent pipeline."""

    @pytest.mark.asyncio
    async def test_transform_project_mode(self, transport: ASGITransport) -> None:
        """Transform the hello-world project through the full pipeline."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/transform",
                json={"input_path": _HELLO_WORLD, "output_directory": "/tmp/test-output"},
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
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/transform", json={"input_path": _STANDALONE_FLOW})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "single_flow"
        assert data["project_name"] is None
        assert data["artifacts"]["mode"] == "single_flow"

    @pytest.mark.asyncio
    async def test_transform_response_shape(self, transport: ASGITransport) -> None:
        """Transform response should have all expected fields."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/transform", json={"input_path": _HELLO_WORLD})
        data = resp.json()
        expected = {"mode", "project_name", "artifacts", "gaps", "warnings", "constructs", "telemetry"}
        assert expected.issubset(data.keys())


class TestIntegrationValidate:
    """Integration tests for POST /validate through ValidatorAgent."""

    @pytest.mark.asyncio
    async def test_validate_returns_report(self, transport: ASGITransport) -> None:
        """Validate endpoint should return a validation report."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/validate", json={"output_directory": "/tmp/output"})
        assert resp.status_code == 200
        data = resp.json()
        assert "valid" in data
        assert "issues" in data
        assert "artifacts_validated" in data
        assert "telemetry" in data

    @pytest.mark.asyncio
    async def test_validate_response_shape(self, transport: ASGITransport) -> None:
        """Validate response should have all expected fields."""
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/validate", json={"output_directory": "/tmp/output"})
        data = resp.json()
        expected = {"valid", "issues", "artifacts_validated", "telemetry"}
        assert expected.issubset(data.keys())
