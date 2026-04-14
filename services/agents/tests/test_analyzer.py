"""Tests for the AnalyzerAgent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from m2la_contracts.enums import InputMode

from m2la_agents.analyzer import AnalyzerAgent
from m2la_agents.models import AgentContext, AgentStatus


class TestAnalyzerAgentHappyPath:
    """Verify AnalyzerAgent succeeds with valid inputs."""

    def test_analyze_standalone_flow(self, standalone_flow_xml: Path, make_context: Any) -> None:
        """Parsing a standalone flow XML should succeed."""
        agent = AnalyzerAgent()
        ctx = make_context(str(standalone_flow_xml))

        result = agent.execute(ctx)

        assert result.status == AgentStatus.SUCCESS
        assert result.agent_name == "AnalyzerAgent"
        assert result.reasoning_summary != ""
        assert result.duration_ms > 0
        assert result.output is not None
        assert "ir" in result.output
        assert "inventory" in result.output
        assert "input_validation" in result.output

    def test_analyze_project(self, hello_world_project: Path, make_context: Any) -> None:
        """Parsing a full project should succeed."""
        agent = AnalyzerAgent()
        ctx = make_context(str(hello_world_project))

        result = agent.execute(ctx)

        assert result.status == AgentStatus.SUCCESS
        assert result.output is not None
        assert result.output["mode"] == InputMode.PROJECT

    def test_accumulated_data_populated(self, standalone_flow_xml: Path, make_context: Any) -> None:
        """After execution, accumulated_data should have ir, inventory, input_validation, input_mode."""
        agent = AnalyzerAgent()
        ctx = make_context(str(standalone_flow_xml))

        agent.execute(ctx)

        assert "ir" in ctx.accumulated_data
        assert "inventory" in ctx.accumulated_data
        assert "input_validation" in ctx.accumulated_data
        assert "input_mode" in ctx.accumulated_data


class TestAnalyzerAgentWithExplicitMode:
    """Verify that explicit mode overrides are honoured."""

    def test_explicit_single_flow_mode(self, standalone_flow_xml: Path, make_context: Any) -> None:
        agent = AnalyzerAgent()
        ctx = make_context(str(standalone_flow_xml), input_mode=InputMode.SINGLE_FLOW)

        result = agent.execute(ctx)

        assert result.status == AgentStatus.SUCCESS
        assert ctx.accumulated_data["input_mode"] == InputMode.SINGLE_FLOW

    def test_explicit_project_mode(self, hello_world_project: Path, make_context: Any) -> None:
        agent = AnalyzerAgent()
        ctx = make_context(str(hello_world_project), input_mode=InputMode.PROJECT)

        result = agent.execute(ctx)

        assert result.status == AgentStatus.SUCCESS
        assert ctx.accumulated_data["input_mode"] == InputMode.PROJECT


class TestAnalyzerAgentErrorHandling:
    """Verify error handling for invalid inputs."""

    def test_nonexistent_path(self, make_context: Any) -> None:
        """Non-existent path should return FAILURE."""
        agent = AnalyzerAgent()
        ctx = make_context("/does/not/exist.xml")

        result = agent.execute(ctx)

        assert result.status == AgentStatus.FAILURE
        assert result.error_message is not None
        assert "does not exist" in result.error_message or "not found" in result.error_message.lower()

    def test_malformed_xml(self, malformed_flow_xml: Path, make_context: Any) -> None:
        """Malformed XML is handled gracefully by the parser (returns 0 flows)."""
        agent = AnalyzerAgent()
        ctx = make_context(str(malformed_flow_xml))

        result = agent.execute(ctx)

        # The parser handles malformed XML gracefully — it returns
        # an empty inventory rather than raising, so the agent succeeds
        # but reports 0 flows.
        assert result.status == AgentStatus.SUCCESS
        assert "0 flow" in result.reasoning_summary

    def test_empty_flow(self, empty_flow_xml: Path, make_context: Any) -> None:
        """Empty flow XML (valid XML, no flows) should succeed but show 0 flows."""
        agent = AnalyzerAgent()
        ctx = make_context(str(empty_flow_xml))

        result = agent.execute(ctx)

        assert result.status == AgentStatus.SUCCESS
        assert "0 flow" in result.reasoning_summary


class TestAnalyzerAgentCorrelationIds:
    """Verify correlation IDs propagate through the context."""

    def test_correlation_id_preserved(self, standalone_flow_xml: Path, make_context: Any) -> None:
        agent = AnalyzerAgent()
        ctx = make_context(str(standalone_flow_xml), correlation_id="my-unique-id-123")

        agent.execute(ctx)

        assert ctx.correlation_id == "my-unique-id-123"

    def test_trace_context_preserved(self, standalone_flow_xml: Path) -> None:
        agent = AnalyzerAgent()
        ctx = AgentContext(
            correlation_id="cid",
            trace_id="trace-abc",
            span_id="span-xyz",
            input_path=str(standalone_flow_xml),
        )

        agent.execute(ctx)

        assert ctx.trace_id == "trace-abc"
        assert ctx.span_id == "span-xyz"


class TestAnalyzerAgentReasoningSummary:
    """Verify reasoning_summary is always populated."""

    def test_success_reasoning(self, standalone_flow_xml: Path, make_context: Any) -> None:
        agent = AnalyzerAgent()
        ctx = make_context(str(standalone_flow_xml))

        result = agent.execute(ctx)

        assert result.reasoning_summary
        assert "Parsed" in result.reasoning_summary

    def test_failure_reasoning(self, make_context: Any) -> None:
        agent = AnalyzerAgent()
        ctx = make_context("/does/not/exist.xml")

        result = agent.execute(ctx)

        assert result.reasoning_summary
        assert "failed" in result.reasoning_summary.lower()
