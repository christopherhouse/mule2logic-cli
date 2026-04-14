"""Tests for the ValidatorAgent."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from m2la_contracts.enums import InputMode
from m2la_contracts.validate import ValidationReport

from m2la_agents.models import AgentStatus
from m2la_agents.validator import ValidatorAgent


class TestValidatorAgentHappyPath:
    """Verify ValidatorAgent succeeds with valid inputs."""

    def test_validate_single_flow_output(self, make_context: Any) -> None:
        """Validating a well-formed workflow dict should succeed."""
        workflow_dict = {
            "definition": {
                "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
                "actions": {},
                "contentVersion": "1.0.0.0",
                "outputs": {},
                "triggers": {},
            },
            "kind": "Stateful",
        }
        agent = ValidatorAgent()
        ctx = make_context(
            accumulated_data={
                "transform_output": workflow_dict,
                "input_mode": InputMode.SINGLE_FLOW,
            },
        )

        result = agent.execute(ctx)

        assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
        assert result.agent_name == "ValidatorAgent"
        assert result.reasoning_summary != ""
        assert result.duration_ms > 0

    def test_validate_project_output(self, make_context: Any, sample_ir: Any, tmp_path: Path) -> None:
        """Validating project output directory should succeed."""
        from m2la_transform.generator import generate_project

        output_dir = tmp_path / "output"
        generate_project(sample_ir, output_dir)

        agent = ValidatorAgent()
        ctx = make_context(
            output_directory=str(output_dir),
            accumulated_data={
                "transform_output": "project_artifacts",  # actual value checked via path
                "input_mode": InputMode.PROJECT,
            },
        )

        result = agent.execute(ctx)

        assert result.status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
        assert isinstance(result.output, ValidationReport)

    def test_accumulated_data_updated(self, make_context: Any) -> None:
        """After execution, context should have output_validation."""
        workflow_dict = {
            "definition": {
                "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
                "actions": {},
                "contentVersion": "1.0.0.0",
                "outputs": {},
                "triggers": {},
            },
            "kind": "Stateful",
        }
        agent = ValidatorAgent()
        ctx = make_context(
            accumulated_data={
                "transform_output": workflow_dict,
                "input_mode": InputMode.SINGLE_FLOW,
            },
        )

        agent.execute(ctx)

        assert "output_validation" in ctx.accumulated_data


class TestValidatorAgentErrorHandling:
    """Verify error handling for missing data."""

    def test_missing_transform_output(self, make_context: Any) -> None:
        """Missing transform output should return FAILURE."""
        agent = ValidatorAgent()
        ctx = make_context(
            accumulated_data={"input_mode": InputMode.PROJECT},
        )

        result = agent.execute(ctx)

        assert result.status == AgentStatus.FAILURE
        assert result.error_message is not None
        assert "transform_output" in result.error_message.lower()

    def test_validate_exception(self, make_context: Any) -> None:
        """An exception during validation should return FAILURE."""
        agent = ValidatorAgent()
        ctx = make_context(
            accumulated_data={
                "transform_output": {"invalid": "data"},
                "input_mode": InputMode.SINGLE_FLOW,
            },
        )

        with patch("m2la_agents.validator.validate_output", side_effect=RuntimeError("validation error")):
            result = agent.execute(ctx)

        assert result.status == AgentStatus.FAILURE
        assert "validation error" in (result.error_message or "")


class TestValidatorAgentCorrelationIds:
    """Verify correlation IDs propagate."""

    def test_correlation_id_preserved(self, make_context: Any) -> None:
        workflow_dict = {
            "definition": {
                "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
                "actions": {},
                "contentVersion": "1.0.0.0",
                "outputs": {},
                "triggers": {},
            },
            "kind": "Stateful",
        }
        agent = ValidatorAgent()
        ctx = make_context(
            correlation_id="validator-cid-55",
            accumulated_data={
                "transform_output": workflow_dict,
                "input_mode": InputMode.SINGLE_FLOW,
            },
        )

        agent.execute(ctx)

        assert ctx.correlation_id == "validator-cid-55"


class TestValidatorAgentReasoningSummary:
    """Verify reasoning_summary is always populated."""

    def test_success_reasoning(self, make_context: Any) -> None:
        workflow_dict = {
            "definition": {
                "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
                "actions": {},
                "contentVersion": "1.0.0.0",
                "outputs": {},
                "triggers": {},
            },
            "kind": "Stateful",
        }
        agent = ValidatorAgent()
        ctx = make_context(
            accumulated_data={
                "transform_output": workflow_dict,
                "input_mode": InputMode.SINGLE_FLOW,
            },
        )

        result = agent.execute(ctx)

        assert result.reasoning_summary
        assert "Validation" in result.reasoning_summary or "validation" in result.reasoning_summary

    def test_failure_reasoning(self, make_context: Any) -> None:
        agent = ValidatorAgent()
        ctx = make_context()

        result = agent.execute(ctx)

        assert result.reasoning_summary
