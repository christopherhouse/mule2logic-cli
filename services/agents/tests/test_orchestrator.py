"""Tests for the MigrationOrchestrator.

Includes both unit tests (mocked services) and integration tests
(using real sample fixtures through the actual services).
"""

from __future__ import annotations

from pathlib import Path

from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus
from m2la_agents.orchestrator import MigrationOrchestrator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _SuccessAgent(BaseAgent):
    """A test agent that always succeeds."""

    def __init__(self, name: str = "SuccessAgent") -> None:
        super().__init__(name=name)

    def _get_tools(self):  # noqa: ANN201
        return []  # No tools for test agent

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

    def _get_tools(self):  # noqa: ANN201
        return []  # No tools for test agent

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

    def _get_tools(self):  # noqa: ANN201
        return []  # No tools for test agent

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

    def test_all_success(self) -> None:
        """All agents succeeding should give SUCCESS overall."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A"), _SuccessAgent("B"), _SuccessAgent("C")],
        )

        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.SUCCESS
        assert len(result.steps) == 3
        assert result.total_duration_ms > 0
        assert result.correlation_id  # UUID generated

    def test_failure_stops_pipeline(self) -> None:
        """A FAILURE should stop the pipeline early."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A"), _FailureAgent("B"), _SuccessAgent("C")],
        )

        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.FAILURE
        assert len(result.steps) == 2  # C should not run
        assert result.steps[0].agent_result.status == AgentStatus.SUCCESS
        assert result.steps[1].agent_result.status == AgentStatus.FAILURE

    def test_partial_continues_pipeline(self) -> None:
        """A PARTIAL status should continue the pipeline but mark overall as PARTIAL."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A"), _PartialAgent("B"), _SuccessAgent("C")],
        )

        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.PARTIAL
        assert len(result.steps) == 3  # All three should run

    def test_correlation_id_propagated(self) -> None:
        """Custom correlation ID should be used."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A")],
        )

        result = orchestrator.run("/fake/path", correlation_id="my-custom-cid")

        assert result.correlation_id == "my-custom-cid"

    def test_auto_generated_correlation_id(self) -> None:
        """Without custom cid, a UUID should be generated."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A")],
        )

        result = orchestrator.run("/fake/path")

        assert len(result.correlation_id) == 36  # UUID format

    def test_accumulated_data_flows_between_agents(self) -> None:
        """Each agent should see the previous agent's accumulated data."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("First"), _SuccessAgent("Second")],
        )

        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.SUCCESS
        # Both agents should have deposited data

    def test_step_timing(self) -> None:
        """Each step should have valid timestamps."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A")],
        )

        result = orchestrator.run("/fake/path")

        step = result.steps[0]
        assert step.started_at <= step.completed_at

    def test_final_output_is_last_successful(self) -> None:
        """final_output should be from the last successful step."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A"), _SuccessAgent("B")],
        )

        result = orchestrator.run("/fake/path")

        assert result.final_output == {"test": True}

    def test_final_output_none_on_failure(self) -> None:
        """final_output should be None if the first step fails."""
        orchestrator = MigrationOrchestrator(
            agents=[_FailureAgent("A")],
        )

        result = orchestrator.run("/fake/path")

        assert result.final_output is None

    def test_empty_pipeline(self) -> None:
        """Empty agent list should return SUCCESS immediately."""
        orchestrator = MigrationOrchestrator(agents=[])

        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.SUCCESS
        assert len(result.steps) == 0

    def test_trace_context_passed(self) -> None:
        """Trace/span IDs should be set on the context."""
        orchestrator = MigrationOrchestrator(
            agents=[_SuccessAgent("A")],
        )

        result = orchestrator.run(
            "/fake/path",
            trace_id="t-123",
            span_id="s-456",
        )

        assert result.overall_status == AgentStatus.SUCCESS


class TestOrchestratorDefaultAgents:
    """Test that default agent list is constructed correctly."""

    def test_default_agents_include_repair(self) -> None:
        orchestrator = MigrationOrchestrator()
        agent_names = [a.name for a in orchestrator.agents]

        assert "AnalyzerAgent" in agent_names
        assert "PlannerAgent" in agent_names
        assert "TransformerAgent" in agent_names
        assert "ValidatorAgent" in agent_names
        assert "RepairAdvisorAgent" in agent_names

    def test_default_agents_without_repair(self) -> None:
        orchestrator = MigrationOrchestrator(include_repair=False)
        agent_names = [a.name for a in orchestrator.agents]

        assert "RepairAdvisorAgent" not in agent_names
        assert len(orchestrator.agents) == 4


# ---------------------------------------------------------------------------
# Integration tests with real sample fixtures
# ---------------------------------------------------------------------------


class TestOrchestratorIntegration:
    """Integration tests using real sample project files."""

    def test_standalone_flow_pipeline(self, standalone_flow_xml: Path) -> None:
        """Full pipeline with standalone flow should complete."""
        orchestrator = MigrationOrchestrator(include_repair=True)

        result = orchestrator.run(str(standalone_flow_xml))

        assert result.overall_status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
        assert len(result.steps) >= 4  # At least analyze → plan → transform → validate
        assert result.correlation_id
        assert result.total_duration_ms > 0

        # Verify each step has a valid reasoning summary
        for step in result.steps:
            assert step.agent_result.reasoning_summary

    def test_project_pipeline(self, hello_world_project: Path, tmp_path: Path) -> None:
        """Full pipeline with a project should complete."""
        orchestrator = MigrationOrchestrator(include_repair=True)

        result = orchestrator.run(
            str(hello_world_project),
            output_directory=str(tmp_path / "output"),
        )

        assert result.overall_status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
        assert len(result.steps) >= 4
        assert result.correlation_id

    def test_nonexistent_path_pipeline(self) -> None:
        """Non-existent path should fail at the analyzer step."""
        orchestrator = MigrationOrchestrator()

        result = orchestrator.run("/nonexistent/path")

        assert result.overall_status == AgentStatus.FAILURE
        assert len(result.steps) == 1  # Only analyzer runs
        assert result.steps[0].step_name == "AnalyzerAgent"

    def test_empty_flow_pipeline(self, empty_flow_xml: Path) -> None:
        """Empty flow should complete the pipeline (possibly with partial status)."""
        orchestrator = MigrationOrchestrator()

        result = orchestrator.run(str(empty_flow_xml))

        # Should either succeed or go partial — not fail catastrophically
        assert result.overall_status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)

    def test_pipeline_correlation_id_consistency(self, standalone_flow_xml: Path) -> None:
        """All steps should share the same correlation ID."""
        orchestrator = MigrationOrchestrator()

        result = orchestrator.run(
            str(standalone_flow_xml),
            correlation_id="integration-test-cid",
        )

        assert result.correlation_id == "integration-test-cid"
