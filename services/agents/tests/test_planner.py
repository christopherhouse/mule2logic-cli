"""Tests for the PlannerAgent."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from m2la_agents.models import AgentStatus, MigrationPlan
from m2la_agents.planner import PlannerAgent


class TestPlannerAgentHappyPath:
    """Verify PlannerAgent succeeds with valid IR in context."""

    def test_plan_with_ir(self, make_context: Any, sample_ir: Any) -> None:
        """PlannerAgent should produce a MigrationPlan when IR is available."""
        agent = PlannerAgent()
        ctx = make_context(accumulated_data={"ir": sample_ir})

        result = agent.execute(ctx)

        assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
        assert result.agent_name == "PlannerAgent"
        assert result.reasoning_summary != ""
        assert result.duration_ms > 0
        assert isinstance(result.output, MigrationPlan)

    def test_plan_flow_count(self, make_context: Any, sample_ir: Any) -> None:
        """Flow count should match the IR."""
        agent = PlannerAgent()
        ctx = make_context(accumulated_data={"ir": sample_ir})

        result = agent.execute(ctx)
        plan = result.output

        assert plan.flow_count == len(sample_ir.flows)

    def test_plan_construct_summary_populated(self, make_context: Any, sample_ir: Any) -> None:
        """Construct summary should be populated."""
        agent = PlannerAgent()
        ctx = make_context(accumulated_data={"ir": sample_ir})

        result = agent.execute(ctx)
        plan = result.output

        assert isinstance(plan.construct_summary, dict)
        assert len(plan.construct_summary) > 0

    def test_accumulated_data_updated(self, make_context: Any, sample_ir: Any) -> None:
        """After execution, context should have migration_plan."""
        agent = PlannerAgent()
        ctx = make_context(accumulated_data={"ir": sample_ir})

        agent.execute(ctx)

        assert "migration_plan" in ctx.accumulated_data
        assert isinstance(ctx.accumulated_data["migration_plan"], MigrationPlan)


class TestPlannerAgentMappingDecisions:
    """Verify mapping decisions in the plan."""

    def test_decisions_present(self, make_context: Any, sample_ir: Any) -> None:
        """Mapping decisions list should have entries."""
        agent = PlannerAgent()
        ctx = make_context(accumulated_data={"ir": sample_ir})

        result = agent.execute(ctx)
        plan = result.output

        assert len(plan.mapping_decisions) > 0

    def test_decision_status_values(self, make_context: Any, sample_ir: Any) -> None:
        """Each decision should have a valid status."""
        agent = PlannerAgent()
        ctx = make_context(accumulated_data={"ir": sample_ir})

        result = agent.execute(ctx)
        plan = result.output

        valid_statuses = {"supported", "unsupported"}
        for decision in plan.mapping_decisions:
            assert decision.status in valid_statuses

    def test_counts_consistent(self, make_context: Any, sample_ir: Any) -> None:
        """Supported + unsupported + partial should equal total constructs."""
        agent = PlannerAgent()
        ctx = make_context(accumulated_data={"ir": sample_ir})

        result = agent.execute(ctx)
        plan = result.output

        total = sum(plan.construct_summary.values())
        assert plan.supported_count + plan.unsupported_count + plan.partial_count == total


class TestPlannerAgentErrorHandling:
    """Verify error handling for missing data."""

    def test_missing_ir(self, make_context: Any) -> None:
        """Missing IR should return FAILURE."""
        agent = PlannerAgent()
        ctx = make_context()

        result = agent.execute(ctx)

        assert result.status == AgentStatus.FAILURE
        assert result.error_message is not None
        assert "ir" in result.error_message.lower()

    def test_missing_mapping_config_graceful(self, make_context: Any, sample_ir: Any) -> None:
        """Missing mapping config files should still produce a plan (all unsupported, PARTIAL status)."""
        agent = PlannerAgent()
        ctx = make_context(accumulated_data={"ir": sample_ir})

        with patch("m2la_agents.planner.load_all", side_effect=FileNotFoundError("test")):
            result = agent.execute(ctx)

        assert result.status == AgentStatus.PARTIAL
        plan = result.output
        assert plan.supported_count == 0


class TestPlannerAgentCorrelationIds:
    """Verify correlation IDs propagate."""

    def test_correlation_id_preserved(self, make_context: Any, sample_ir: Any) -> None:
        agent = PlannerAgent()
        ctx = make_context(
            correlation_id="planner-correlation-42",
            accumulated_data={"ir": sample_ir},
        )

        agent.execute(ctx)

        assert ctx.correlation_id == "planner-correlation-42"


class TestPlannerAgentReasoningSummary:
    """Verify reasoning_summary is always populated."""

    def test_success_reasoning(self, make_context: Any, sample_ir: Any) -> None:
        agent = PlannerAgent()
        ctx = make_context(accumulated_data={"ir": sample_ir})

        result = agent.execute(ctx)

        assert result.reasoning_summary
        assert "Plan for" in result.reasoning_summary

    def test_failure_reasoning(self, make_context: Any) -> None:
        agent = PlannerAgent()
        ctx = make_context()

        result = agent.execute(ctx)

        assert result.reasoning_summary
        assert "ir" in result.reasoning_summary.lower() or "IR" in result.reasoning_summary
