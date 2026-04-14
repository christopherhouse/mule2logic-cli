"""Tests for Azure AI Agents SDK integration.

These tests verify:

* ``_register_tools()`` is called and populates the ``toolset``.
* ``create_on_service()`` and ``cleanup()`` work with a mocked client.
* Offline vs online mode selection in the orchestrator.
* ``FunctionTool`` wrappers produce valid JSON output.
* ``AgentsClientConfig`` defaults and validation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from azure.ai.agents.models import FunctionTool, ToolSet

from m2la_agents.analyzer import AnalyzerAgent
from m2la_agents.base import BaseAgent
from m2la_agents.function_tools import (
    analyze_mule_input,
    create_migration_plan,
    suggest_repairs,
    transform_to_logic_apps,
)
from m2la_agents.models import AgentContext, AgentResult, AgentStatus
from m2la_agents.orchestrator import MigrationOrchestrator
from m2la_agents.planner import PlannerAgent
from m2la_agents.repair_advisor import RepairAdvisorAgent
from m2la_agents.sdk_config import AgentsClientConfig
from m2la_agents.transformer import TransformerAgent
from m2la_agents.validator import ValidatorAgent

# ---------------------------------------------------------------------------
# AgentsClientConfig
# ---------------------------------------------------------------------------


class TestAgentsClientConfig:
    """Verify SDK configuration model."""

    def test_defaults(self) -> None:
        config = AgentsClientConfig()
        assert config.endpoint is None
        assert config.model_deployment == "gpt-4o"

    def test_custom_values(self) -> None:
        config = AgentsClientConfig(
            endpoint="https://my-project.api.azureml.ms",
            model_deployment="gpt-4o-mini",
        )
        assert config.endpoint == "https://my-project.api.azureml.ms"
        assert config.model_deployment == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# _register_tools() and toolset population
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Verify that each agent registers tools on construction."""

    @pytest.mark.parametrize(
        "agent_cls",
        [AnalyzerAgent, PlannerAgent, TransformerAgent, ValidatorAgent, RepairAdvisorAgent],
    )
    def test_toolset_populated(self, agent_cls: type[BaseAgent]) -> None:
        """Each agent should have a non-empty toolset after construction."""
        agent = agent_cls()
        assert isinstance(agent.toolset, ToolSet)
        # The toolset should have at least one tool definition
        defs = agent.toolset.definitions
        assert len(defs) > 0

    @pytest.mark.parametrize(
        "agent_cls",
        [AnalyzerAgent, PlannerAgent, TransformerAgent, ValidatorAgent, RepairAdvisorAgent],
    )
    def test_instructions_set(self, agent_cls: type[BaseAgent]) -> None:
        """Each agent should have non-empty instructions."""
        agent = agent_cls()
        assert agent.instructions
        assert len(agent.instructions) > 20

    @pytest.mark.parametrize(
        "agent_cls",
        [AnalyzerAgent, PlannerAgent, TransformerAgent, ValidatorAgent, RepairAdvisorAgent],
    )
    def test_offline_mode_by_default(self, agent_cls: type[BaseAgent]) -> None:
        """Agents should start in offline mode (no sdk_agent_id)."""
        agent = agent_cls()
        assert agent.sdk_agent_id is None

    @pytest.mark.parametrize(
        "agent_cls",
        [AnalyzerAgent, PlannerAgent, TransformerAgent, ValidatorAgent, RepairAdvisorAgent],
    )
    def test_repr_offline(self, agent_cls: type[BaseAgent]) -> None:
        """repr should indicate offline mode."""
        agent = agent_cls()
        assert "offline" in repr(agent)


# ---------------------------------------------------------------------------
# create_on_service() / cleanup() with mocked client
# ---------------------------------------------------------------------------


class TestSDKLifecycle:
    """Verify create_on_service / cleanup with a mocked AgentsClient."""

    def _make_mock_client(self) -> MagicMock:
        """Create a mock AgentsClient with expected methods."""
        client = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "agent-id-12345"
        client.create_agent.return_value = mock_agent
        return client

    def test_create_on_service(self) -> None:
        agent = AnalyzerAgent()
        client = self._make_mock_client()

        agent_id = agent.create_on_service(client, "gpt-4o")

        assert agent_id == "agent-id-12345"
        assert agent.sdk_agent_id == "agent-id-12345"
        client.create_agent.assert_called_once_with(
            model="gpt-4o",
            name="AnalyzerAgent",
            instructions=agent.instructions,
            toolset=agent.toolset,
        )

    def test_cleanup(self) -> None:
        agent = AnalyzerAgent()
        client = self._make_mock_client()

        agent.create_on_service(client, "gpt-4o")
        assert agent.sdk_agent_id is not None

        agent.cleanup(client)

        assert agent.sdk_agent_id is None
        client.delete_agent.assert_called_once_with("agent-id-12345")

    def test_cleanup_noop_when_offline(self) -> None:
        """cleanup() should be a no-op when agent is in offline mode."""
        agent = AnalyzerAgent()
        client = self._make_mock_client()

        agent.cleanup(client)

        client.delete_agent.assert_not_called()
        assert agent.sdk_agent_id is None

    def test_repr_online_after_create(self) -> None:
        agent = AnalyzerAgent()
        client = self._make_mock_client()

        agent.create_on_service(client, "gpt-4o")

        assert "online" in repr(agent)

    @pytest.mark.parametrize(
        "agent_cls",
        [AnalyzerAgent, PlannerAgent, TransformerAgent, ValidatorAgent, RepairAdvisorAgent],
    )
    def test_all_agents_create_and_cleanup(self, agent_cls: type[BaseAgent]) -> None:
        """Every agent type should round-trip through create/cleanup."""
        agent = agent_cls()
        client = self._make_mock_client()

        agent_id = agent.create_on_service(client, "gpt-4o")
        assert agent.sdk_agent_id == agent_id

        agent.cleanup(client)
        assert agent.sdk_agent_id is None


# ---------------------------------------------------------------------------
# Orchestrator mode selection
# ---------------------------------------------------------------------------


class TestOrchestratorModeSelection:
    """Verify the orchestrator selects online/offline based on client."""

    def test_offline_when_no_client(self) -> None:
        """Without a client, orchestrator should use offline mode."""
        orchestrator = MigrationOrchestrator(client=None)
        assert orchestrator.client is None

    def test_online_when_client_provided(self) -> None:
        """With a client, orchestrator should use online mode."""
        mock_client = MagicMock()
        orchestrator = MigrationOrchestrator(client=mock_client)
        assert orchestrator.client is mock_client

    def test_config_defaults(self) -> None:
        orchestrator = MigrationOrchestrator()
        assert orchestrator.config.endpoint is None
        assert orchestrator.config.model_deployment == "gpt-4o"

    def test_custom_config(self) -> None:
        config = AgentsClientConfig(model_deployment="gpt-4o-mini")
        orchestrator = MigrationOrchestrator(config=config)
        assert orchestrator.config.model_deployment == "gpt-4o-mini"

    def test_offline_run_uses_execute(self, standalone_flow_xml: Path) -> None:
        """In offline mode, the orchestrator should call agent.execute()."""
        orchestrator = MigrationOrchestrator(include_repair=True)
        result = orchestrator.run(str(standalone_flow_xml))

        # Should complete (same as existing tests)
        assert result.overall_status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
        assert len(result.steps) >= 4

    def test_online_run_creates_and_cleans_agents(self) -> None:
        """In online mode, orchestrator should create and clean up agents."""

        class _StubAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__(name="StubAgent")

            def _register_tools(self) -> None:
                pass

            def execute(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.SUCCESS,
                    output={"stub": True},
                    reasoning_summary="Stub completed",
                    duration_ms=1.0,
                )

        mock_client = MagicMock()
        mock_agent_obj = MagicMock()
        mock_agent_obj.id = "stub-agent-id"
        mock_client.create_agent.return_value = mock_agent_obj

        mock_thread = MagicMock()
        mock_thread.id = "thread-id"
        mock_client.threads.create.return_value = mock_thread

        mock_run = MagicMock()
        mock_run.status = "completed"
        mock_run.id = "run-id"
        mock_client.runs.create_and_process.return_value = mock_run

        orchestrator = MigrationOrchestrator(
            agents=[_StubAgent()],
            client=mock_client,
        )
        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.SUCCESS
        mock_client.create_agent.assert_called_once()
        mock_client.delete_agent.assert_called_once_with("stub-agent-id")


# ---------------------------------------------------------------------------
# FunctionTool wrappers
# ---------------------------------------------------------------------------


class TestFunctionToolWrappers:
    """Verify that function_tools functions produce valid JSON."""

    def test_analyze_mule_input(self, standalone_flow_xml: Path) -> None:
        import json

        result_str = analyze_mule_input(str(standalone_flow_xml))
        data = json.loads(result_str)

        assert "flow_count" in data
        assert "subflow_count" in data
        assert "construct_count" in data
        assert "warnings" in data
        assert "mode" in data
        assert "validation_valid" in data

    def test_analyze_mule_input_with_mode(self, standalone_flow_xml: Path) -> None:
        import json

        result_str = analyze_mule_input(str(standalone_flow_xml), mode="single_flow")
        data = json.loads(result_str)

        assert data["mode"] == "single_flow"

    def test_create_migration_plan(self) -> None:
        import json

        ir_json = json.dumps({"construct_names": ["http_listener", "logger"], "flow_count": 1})
        result_str = create_migration_plan(ir_json)
        data = json.loads(result_str)

        assert "flow_count" in data
        assert "construct_summary" in data
        assert "supported_count" in data
        assert "unsupported_count" in data
        assert "mapping_decisions" in data

    def test_transform_to_logic_apps(self) -> None:
        import json

        ir_json = json.dumps({"flow_count": 2})
        result_str = transform_to_logic_apps(ir_json, mode="project", output_directory="/tmp/out")
        data = json.loads(result_str)

        assert data["mode"] == "project"
        assert data["flow_count"] == 2

    def test_suggest_repairs(self) -> None:
        import json

        issues_json = json.dumps([{"rule_id": "OUT_001", "message": "Bad schema", "severity": "error"}])
        gaps_json = json.dumps([{"category": "unsupported_construct", "construct_name": "scatter-gather"}])
        result_str = suggest_repairs(issues_json, gaps_json)
        data = json.loads(result_str)

        assert isinstance(data, list)
        assert len(data) == 2

    def test_function_tool_wrapping(self) -> None:
        """Verify that functions can be wrapped in FunctionTool."""
        ft = FunctionTool({analyze_mule_input})
        assert ft is not None

        ft2 = FunctionTool({create_migration_plan})
        assert ft2 is not None

        ft3 = FunctionTool({suggest_repairs})
        assert ft3 is not None
