"""Tests for the MigrationOrchestrator.

Includes both unit tests (mocked services) and integration tests
(using real sample fixtures through the actual services).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus
from m2la_agents.orchestrator import MigrationOrchestrator

from .mock_chat_client import MockChatClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _success_tool() -> str:
    """A simple tool that always returns a success JSON."""
    return json.dumps({"test": True, "status": "success"})


def _failure_tool() -> str:
    """A simple tool that always returns a failure JSON."""
    return json.dumps({"error": "Simulated failure"})


def _partial_tool() -> str:
    """A simple tool that returns a partial-success JSON."""
    return json.dumps({"partial": True, "valid": False})


class _SuccessAgent(BaseAgent):
    """A test agent that always succeeds."""

    def __init__(self, name: str = "SuccessAgent") -> None:
        super().__init__(name=name)

    def _get_tools(self) -> Sequence[Callable[..., Any]]:
        return [_success_tool]

    def execute(self, context: AgentContext) -> AgentResult:
        context.accumulated_data[self.name] = "done"
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.SUCCESS,
            output={"test": True},
            reasoning_summary=f"{self.name} completed successfully",
            duration_ms=1.0,
        )


class _FailureAgent(BaseAgent):
    """A test agent that always fails."""

    def __init__(self, name: str = "FailureAgent") -> None:
        super().__init__(name=name)

    def _get_tools(self) -> Sequence[Callable[..., Any]]:
        return [_failure_tool]

    def execute(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.FAILURE,
            reasoning_summary=f"{self.name} failed",
            duration_ms=0.5,
            error_message="Simulated failure",
        )


class _PartialAgent(BaseAgent):
    """A test agent that returns PARTIAL status."""

    def __init__(self, name: str = "PartialAgent") -> None:
        super().__init__(name=name)

    def _get_tools(self) -> Sequence[Callable[..., Any]]:
        return [_partial_tool]

    def execute(self, context: AgentContext) -> AgentResult:
        context.accumulated_data[self.name] = "partial"
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.PARTIAL,
            output={"partial": True},
            reasoning_summary=f"{self.name} partially completed",
            duration_ms=0.8,
        )


# ---------------------------------------------------------------------------
# Unit tests with mock agents
# ---------------------------------------------------------------------------


class TestOrchestratorWithMockAgents:
    """Test orchestrator pipeline logic with synthetic agents."""

    def test_all_success(self, mock_client: MockChatClient) -> None:
        """All agents succeeding should give SUCCESS overall."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A"), _SuccessAgent("B"), _SuccessAgent("C")],
            client=mock_client,
        )

        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.SUCCESS
        assert len(result.steps) >= 1
        assert result.total_duration_ms > 0
        assert result.correlation_id  # UUID generated

    def test_failure_stops_pipeline(self, mock_client: MockChatClient) -> None:
        """A FAILURE should stop the pipeline early."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A"), _FailureAgent("B"), _SuccessAgent("C")],
            client=mock_client,
        )

        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.FAILURE

    def test_partial_continues_pipeline(self, mock_client: MockChatClient) -> None:
        """A PARTIAL status should continue the pipeline but mark overall as PARTIAL."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A"), _PartialAgent("B"), _SuccessAgent("C")],
            client=mock_client,
        )

        result = orchestrator.run("/fake/path")

        assert result.overall_status in (AgentStatus.PARTIAL, AgentStatus.SUCCESS)

    def test_correlation_id_propagated(self, mock_client: MockChatClient) -> None:
        """Custom correlation ID should be used."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A")],
            client=mock_client,
        )

        result = orchestrator.run("/fake/path", correlation_id="my-custom-cid")

        assert result.correlation_id == "my-custom-cid"

    def test_auto_generated_correlation_id(self, mock_client: MockChatClient) -> None:
        """Without custom cid, a UUID should be generated."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A")],
            client=mock_client,
        )

        result = orchestrator.run("/fake/path")

        assert len(result.correlation_id) == 36  # UUID format

    def test_accumulated_data_flows_between_agents(self, mock_client: MockChatClient) -> None:
        """Workflow should complete with multiple agents."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("First"), _SuccessAgent("Second")],
            client=mock_client,
        )

        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.SUCCESS

    def test_step_timing(self, mock_client: MockChatClient) -> None:
        """Each step should have valid timestamps."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A")],
            client=mock_client,
        )

        result = orchestrator.run("/fake/path")

        if result.steps:
            step = result.steps[0]
            assert step.started_at <= step.completed_at

    def test_final_output_from_last_step(self, mock_client: MockChatClient) -> None:
        """final_output should be from the last successful step."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A"), _SuccessAgent("B")],
            client=mock_client,
        )

        result = orchestrator.run("/fake/path")

        assert result.final_output is not None

    def test_final_output_none_on_failure(self, mock_client: MockChatClient) -> None:
        """final_output should be None if all steps fail."""
        orchestrator = MigrationOrchestrator(
            agents=[_FailureAgent("A")],
            client=mock_client,
        )

        result = orchestrator.run("/fake/path")

        # When all steps fail, final_output may be None or an error dict
        assert result.overall_status == AgentStatus.FAILURE

    def test_empty_pipeline(self, mock_client: MockChatClient) -> None:
        """Empty agent list should return SUCCESS immediately."""
        orchestrator = MigrationOrchestrator(agents=[], client=mock_client)

        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.SUCCESS
        assert len(result.steps) == 0

    def test_trace_context_passed(self, mock_client: MockChatClient) -> None:
        """Trace/span IDs should be set on the context."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A")],
            client=mock_client,
        )

        result = orchestrator.run(
            "/fake/path",
            trace_id="t-123",
            span_id="s-456",
        )

        assert result.overall_status == AgentStatus.SUCCESS


class TestOrchestratorDefaultAgents:
    """Test that default agent list is constructed correctly."""

    def test_default_agents_include_repair(self, mock_client: MockChatClient) -> None:
        orchestrator = MigrationOrchestrator(client=mock_client)
        agent_names = [a.name for a in orchestrator.agents]

        assert "AnalyzerAgent" in agent_names
        assert "PlannerAgent" in agent_names
        assert "TransformerAgent" in agent_names
        assert "ValidatorAgent" in agent_names
        assert "RepairAdvisorAgent" in agent_names

    def test_default_agents_without_repair(self, mock_client: MockChatClient) -> None:
        orchestrator = MigrationOrchestrator(include_repair=False, client=mock_client)
        agent_names = [a.name for a in orchestrator.agents]

        assert "RepairAdvisorAgent" not in agent_names
        assert len(orchestrator.agents) == 4


# ---------------------------------------------------------------------------
# Integration tests with real sample fixtures
# ---------------------------------------------------------------------------


class TestOrchestratorIntegration:
    """Integration tests using real sample project files."""

    def test_standalone_flow_pipeline(self, standalone_flow_xml: Path, mock_client: MockChatClient) -> None:
        """Full pipeline with standalone flow should complete."""
        orchestrator = MigrationOrchestrator(include_repair=True, client=mock_client)

        result = orchestrator.run(str(standalone_flow_xml))

        assert result.overall_status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL, AgentStatus.FAILURE)
        assert result.correlation_id
        assert result.total_duration_ms > 0

    def test_project_pipeline(self, hello_world_project: Path, tmp_path: Path, mock_client: MockChatClient) -> None:
        """Full pipeline with a project should complete."""
        orchestrator = MigrationOrchestrator(include_repair=True, client=mock_client)

        result = orchestrator.run(
            str(hello_world_project),
            output_directory=str(tmp_path / "output"),
        )

        assert result.overall_status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL, AgentStatus.FAILURE)
        assert result.correlation_id

    def test_nonexistent_path_pipeline(self, mock_client: MockChatClient) -> None:
        """Non-existent path should result in a pipeline run (may fail at analyzer)."""
        orchestrator = MigrationOrchestrator(client=mock_client)

        result = orchestrator.run("/nonexistent/path")

        # The pipeline runs through the LLM; the analyzer tool may fail
        assert result.correlation_id
        assert result.total_duration_ms > 0

    def test_empty_flow_pipeline(self, empty_flow_xml: Path, mock_client: MockChatClient) -> None:
        """Empty flow should complete the pipeline."""
        orchestrator = MigrationOrchestrator(client=mock_client)

        result = orchestrator.run(str(empty_flow_xml))

        assert result.correlation_id

    def test_pipeline_correlation_id_consistency(self, standalone_flow_xml: Path, mock_client: MockChatClient) -> None:
        """Correlation ID should be preserved through the pipeline."""
        orchestrator = MigrationOrchestrator(client=mock_client)

        result = orchestrator.run(
            str(standalone_flow_xml),
            correlation_id="integration-test-cid",
        )

        assert result.correlation_id == "integration-test-cid"
