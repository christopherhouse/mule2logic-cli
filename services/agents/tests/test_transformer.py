"""Tests for the TransformerAgent."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from m2la_contracts.enums import InputMode

from m2la_agents.base import AgentStatus
from m2la_agents.transformer import TransformerAgent


class TestTransformerAgentHappyPath:
    """Verify TransformerAgent succeeds with valid inputs."""

    def test_transform_single_flow(self, make_context: Any, sample_single_flow_ir: Any) -> None:
        """Single-flow mode should generate a workflow dict."""
        agent = TransformerAgent()
        ctx = make_context(
            accumulated_data={
                "ir": sample_single_flow_ir,
                "input_mode": InputMode.SINGLE_FLOW,
            },
        )

        result = agent.execute(ctx)

        assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
        assert result.agent_name == "TransformerAgent"
        assert result.reasoning_summary != ""
        assert result.duration_ms > 0
        assert result.output is not None

    def test_transform_project(self, make_context: Any, sample_ir: Any, tmp_path: Path) -> None:
        """Project mode should generate artifacts to the output directory."""
        agent = TransformerAgent()
        ctx = make_context(
            output_directory=str(tmp_path / "output"),
            accumulated_data={
                "ir": sample_ir,
                "input_mode": InputMode.PROJECT,
            },
        )

        result = agent.execute(ctx)

        assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
        assert "artifacts" in result.output
        assert "gaps" in result.output

    def test_accumulated_data_updated(self, make_context: Any, sample_single_flow_ir: Any) -> None:
        """After execution, context should have transform_output and migration_gaps."""
        agent = TransformerAgent()
        ctx = make_context(
            accumulated_data={
                "ir": sample_single_flow_ir,
                "input_mode": InputMode.SINGLE_FLOW,
            },
        )

        agent.execute(ctx)

        assert "transform_output" in ctx.accumulated_data
        assert "migration_gaps" in ctx.accumulated_data

    def test_ir_validation_performed(self, make_context: Any, sample_ir: Any, tmp_path: Path) -> None:
        """IR validation report should be stored in accumulated_data."""
        agent = TransformerAgent()
        ctx = make_context(
            output_directory=str(tmp_path / "output"),
            accumulated_data={
                "ir": sample_ir,
                "input_mode": InputMode.PROJECT,
            },
        )

        agent.execute(ctx)

        assert "ir_validation" in ctx.accumulated_data


class TestTransformerAgentErrorHandling:
    """Verify error handling for missing data."""

    def test_missing_ir(self, make_context: Any) -> None:
        """Missing IR should return FAILURE."""
        agent = TransformerAgent()
        ctx = make_context(accumulated_data={"input_mode": InputMode.PROJECT})

        result = agent.execute(ctx)

        assert result.status == AgentStatus.FAILURE
        assert result.error_message is not None
        assert "ir" in result.error_message.lower()

    def test_empty_flows_single_flow(self, make_context: Any) -> None:
        """Single-flow with no flows should produce warnings."""
        from m2la_ir.builders import build_single_flow_ir

        empty_ir = build_single_flow_ir(source_path="/fake.xml", flows=[])
        agent = TransformerAgent()
        ctx = make_context(
            accumulated_data={
                "ir": empty_ir,
                "input_mode": InputMode.SINGLE_FLOW,
            },
        )

        result = agent.execute(ctx)

        # Should succeed or be partial, but have a warning about no flows
        assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
        assert any("No flows" in w for w in result.warnings)

    def test_transform_exception(self, make_context: Any, sample_ir: Any) -> None:
        """An exception during transform should return FAILURE."""
        agent = TransformerAgent()
        ctx = make_context(
            accumulated_data={
                "ir": sample_ir,
                "input_mode": InputMode.PROJECT,
            },
        )

        with patch("m2la_agents.transformer.generate_project", side_effect=RuntimeError("boom")):
            result = agent.execute(ctx)

        assert result.status == AgentStatus.FAILURE
        assert "boom" in (result.error_message or "")


class TestTransformerAgentCorrelationIds:
    """Verify correlation IDs propagate."""

    def test_correlation_id_preserved(self, make_context: Any, sample_single_flow_ir: Any) -> None:
        agent = TransformerAgent()
        ctx = make_context(
            correlation_id="transform-cid-99",
            accumulated_data={
                "ir": sample_single_flow_ir,
                "input_mode": InputMode.SINGLE_FLOW,
            },
        )

        agent.execute(ctx)

        assert ctx.correlation_id == "transform-cid-99"


class TestTransformerAgentReasoningSummary:
    """Verify reasoning_summary is always populated."""

    def test_success_reasoning(self, make_context: Any, sample_single_flow_ir: Any) -> None:
        agent = TransformerAgent()
        ctx = make_context(
            accumulated_data={
                "ir": sample_single_flow_ir,
                "input_mode": InputMode.SINGLE_FLOW,
            },
        )

        result = agent.execute(ctx)

        assert result.reasoning_summary
        assert "Generated" in result.reasoning_summary

    def test_failure_reasoning(self, make_context: Any) -> None:
        agent = TransformerAgent()
        ctx = make_context()

        result = agent.execute(ctx)

        assert result.reasoning_summary
        # Should mention the failure
        assert "failed" in result.reasoning_summary.lower() or "No IR" in result.reasoning_summary
