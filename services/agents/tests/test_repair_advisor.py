"""Tests for the RepairAdvisorAgent."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from m2la_contracts.enums import GapCategory, Severity, ValidationCategory
from m2la_contracts.validate import ValidationIssue, ValidationReport

from m2la_agents.base import AgentStatus
from m2la_agents.repair_advisor import RepairAdvisorAgent, RepairSuggestion


def _make_report(*, issues: list[ValidationIssue] | None = None, valid: bool = True) -> ValidationReport:
    """Helper to build a ValidationReport."""
    return ValidationReport(
        valid=valid,
        issues=issues or [],
        artifacts_validated=1,
    )


def _make_issue(
    rule_id: str = "OUT_001",
    message: str = "Test issue",
    severity: Severity = Severity.ERROR,
) -> ValidationIssue:
    """Helper to build a ValidationIssue."""
    return ValidationIssue(
        rule_id=rule_id,
        message=message,
        severity=severity,
        category=ValidationCategory.OUTPUT_INTEGRITY,
    )


class TestRepairAdvisorHappyPath:
    """Verify RepairAdvisorAgent with valid inputs."""

    def test_no_issues_no_gaps(self, make_context: Any) -> None:
        """When there are no issues or gaps, should return empty suggestions."""
        agent = RepairAdvisorAgent()
        report = _make_report(valid=True)
        ctx = make_context(
            accumulated_data={
                "output_validation": report,
                "migration_gaps": [],
            },
        )

        result = agent.execute(ctx)

        assert result.status == AgentStatus.SUCCESS
        assert result.agent_name == "RepairAdvisorAgent"
        assert result.reasoning_summary != ""
        assert "No repairs needed" in result.reasoning_summary
        assert result.output == []

    def test_with_validation_issues(self, make_context: Any) -> None:
        """Validation issues should produce repair suggestions."""
        issues = [_make_issue(rule_id="OUT_001", message="Bad schema")]
        report = _make_report(issues=issues, valid=False)
        agent = RepairAdvisorAgent()
        ctx = make_context(
            accumulated_data={
                "output_validation": report,
                "migration_gaps": [],
            },
        )

        result = agent.execute(ctx)

        assert result.status == AgentStatus.SUCCESS
        assert len(result.output) > 0
        assert isinstance(result.output[0], RepairSuggestion)
        assert result.output[0].issue_ref == "OUT_001"

    def test_with_migration_gaps(self, make_context: Any) -> None:
        """Migration gaps should produce repair suggestions."""
        gap = MagicMock()
        gap.category = GapCategory.UNSUPPORTED_CONSTRUCT
        gap.construct_name = "scatter-gather"

        agent = RepairAdvisorAgent()
        ctx = make_context(
            accumulated_data={
                "output_validation": _make_report(),
                "migration_gaps": [gap],
            },
        )

        result = agent.execute(ctx)

        assert result.status == AgentStatus.SUCCESS
        assert len(result.output) > 0
        gap_suggestion = [s for s in result.output if s.issue_ref == "scatter-gather"]
        assert len(gap_suggestion) == 1
        assert "Azure Function" in gap_suggestion[0].suggestion

    def test_accumulated_data_updated(self, make_context: Any) -> None:
        """After execution, context should have repair_suggestions."""
        agent = RepairAdvisorAgent()
        ctx = make_context(
            accumulated_data={
                "output_validation": _make_report(),
                "migration_gaps": [],
            },
        )

        agent.execute(ctx)

        assert "repair_suggestions" in ctx.accumulated_data


class TestRepairAdvisorRuleMapping:
    """Verify rule_id prefix matching for different issue types."""

    def test_mule_prefix(self, make_context: Any) -> None:
        issues = [_make_issue(rule_id="MULE_001", severity=Severity.ERROR)]
        report = _make_report(issues=issues, valid=False)
        agent = RepairAdvisorAgent()
        ctx = make_context(accumulated_data={"output_validation": report})

        result = agent.execute(ctx)

        assert len(result.output) > 0
        assert result.output[0].issue_ref == "MULE_001"

    def test_ir_prefix(self, make_context: Any) -> None:
        issues = [_make_issue(rule_id="IR_001", severity=Severity.ERROR)]
        report = _make_report(issues=issues, valid=False)
        agent = RepairAdvisorAgent()
        ctx = make_context(accumulated_data={"output_validation": report})

        result = agent.execute(ctx)

        assert len(result.output) > 0
        assert result.output[0].issue_ref == "IR_001"

    def test_unknown_prefix_with_error_severity(self, make_context: Any) -> None:
        """Unknown rule IDs with error severity should still get suggestions."""
        issues = [_make_issue(rule_id="CUSTOM_001", severity=Severity.ERROR)]
        report = _make_report(issues=issues, valid=False)
        agent = RepairAdvisorAgent()
        ctx = make_context(accumulated_data={"output_validation": report})

        result = agent.execute(ctx)

        assert len(result.output) > 0
        assert result.output[0].confidence == "low"


class TestRepairAdvisorGapCategories:
    """Verify gap category mapping."""

    @pytest.mark.parametrize(
        "category",
        [
            GapCategory.UNSUPPORTED_CONSTRUCT,
            GapCategory.UNRESOLVABLE_REFERENCE,
            GapCategory.PARTIAL_SUPPORT,
            GapCategory.CONNECTOR_MISMATCH,
            GapCategory.DATAWEAVE_COMPLEXITY,
        ],
    )
    def test_known_gap_categories(self, make_context: Any, category: GapCategory) -> None:
        gap = MagicMock()
        gap.category = category
        gap.construct_name = f"test-{category.value}"

        agent = RepairAdvisorAgent()
        ctx = make_context(accumulated_data={"migration_gaps": [gap]})

        result = agent.execute(ctx)

        assert result.status == AgentStatus.SUCCESS
        assert len(result.output) > 0


class TestRepairAdvisorCorrelationIds:
    """Verify correlation IDs propagate."""

    def test_correlation_id_preserved(self, make_context: Any) -> None:
        agent = RepairAdvisorAgent()
        ctx = make_context(
            correlation_id="repair-cid-77",
            accumulated_data={
                "output_validation": _make_report(),
                "migration_gaps": [],
            },
        )

        agent.execute(ctx)

        assert ctx.correlation_id == "repair-cid-77"


class TestRepairAdvisorReasoningSummary:
    """Verify reasoning_summary is always populated."""

    def test_no_issues_reasoning(self, make_context: Any) -> None:
        agent = RepairAdvisorAgent()
        ctx = make_context(
            accumulated_data={
                "output_validation": _make_report(),
                "migration_gaps": [],
            },
        )

        result = agent.execute(ctx)

        assert "No repairs needed" in result.reasoning_summary

    def test_with_issues_reasoning(self, make_context: Any) -> None:
        issues = [_make_issue()]
        report = _make_report(issues=issues, valid=False)
        agent = RepairAdvisorAgent()
        ctx = make_context(
            accumulated_data={
                "output_validation": report,
                "migration_gaps": [],
            },
        )

        result = agent.execute(ctx)

        assert "suggestion" in result.reasoning_summary.lower()
