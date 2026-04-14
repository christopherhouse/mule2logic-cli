"""Tests for Microsoft Agent Framework (MAF) integration.

These tests verify:

* ``_get_tools()`` returns the correct tool functions.
* ``build_maf_agent()`` produces a MAF ``Agent`` with tools registered.
* Offline vs online mode selection in the orchestrator.
* ``FoundryClientConfig`` defaults and validation.
* Rich system prompts are loaded and used.
* Function tool wrappers produce valid JSON output.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest

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
from m2la_agents.prompts import (
    analyzer_prompt,
    orchestrator_prompt,
    planner_prompt,
    repair_advisor_prompt,
    transformer_prompt,
    validator_prompt,
)
from m2la_agents.repair_advisor import RepairAdvisorAgent
from m2la_agents.sdk_config import FoundryClientConfig
from m2la_agents.transformer import TransformerAgent
from m2la_agents.validator import ValidatorAgent

# ---------------------------------------------------------------------------
# FoundryClientConfig
# ---------------------------------------------------------------------------


class TestFoundryClientConfig:
    """Verify MAF configuration model."""

    def test_defaults(self) -> None:
        config = FoundryClientConfig()
        assert config.endpoint is None
        assert config.model == "gpt-4o"

    def test_custom_values(self) -> None:
        config = FoundryClientConfig(
            endpoint="https://my-project.api.azureml.ms",
            model="gpt-4o-mini",
        )
        assert config.endpoint == "https://my-project.api.azureml.ms"
        assert config.model == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------


class TestSystemPrompts:
    """Verify that system prompts are rich, non-trivial, and used by agents."""

    def test_orchestrator_prompt_exists(self) -> None:
        prompt = orchestrator_prompt()
        assert len(prompt) > 200
        assert "Migration Orchestrator" in prompt
        assert "sub-agent" in prompt.lower() or "delegate" in prompt.lower()

    def test_analyzer_prompt_used(self) -> None:
        agent = AnalyzerAgent()
        assert agent.instructions == analyzer_prompt()
        assert "analyze_mule_input" in agent.instructions

    def test_planner_prompt_used(self) -> None:
        agent = PlannerAgent()
        assert agent.instructions == planner_prompt()
        assert "migration plan" in agent.instructions.lower()

    def test_transformer_prompt_used(self) -> None:
        agent = TransformerAgent()
        assert agent.instructions == transformer_prompt()
        assert "transform" in agent.instructions.lower()

    def test_validator_prompt_used(self) -> None:
        agent = ValidatorAgent()
        assert agent.instructions == validator_prompt()
        assert "validate" in agent.instructions.lower()

    def test_repair_prompt_used(self) -> None:
        agent = RepairAdvisorAgent()
        assert agent.instructions == repair_advisor_prompt()
        assert "repair" in agent.instructions.lower()

    @pytest.mark.parametrize(
        "prompt_fn",
        [analyzer_prompt, planner_prompt, transformer_prompt, validator_prompt, repair_advisor_prompt],
    )
    def test_prompts_are_substantial(self, prompt_fn: Callable[[], str]) -> None:
        """Each prompt should contain meaningful domain-specific instructions."""
        prompt = prompt_fn()
        assert len(prompt) > 200
        # Should mention the tool or the domain
        lower = prompt.lower()
        assert "mulesoft" in lower or "logic apps" in lower or "migration" in lower


# ---------------------------------------------------------------------------
# _get_tools() and tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Verify that each agent returns tools via _get_tools()."""

    @pytest.mark.parametrize(
        "agent_cls",
        [AnalyzerAgent, PlannerAgent, TransformerAgent, ValidatorAgent, RepairAdvisorAgent],
    )
    def test_get_tools_returns_callables(self, agent_cls: type[BaseAgent]) -> None:
        """Each agent should return a non-empty list of callables from _get_tools()."""
        agent = agent_cls()
        tools = agent._get_tools()  # noqa: SLF001
        assert isinstance(tools, (list, tuple, Sequence))
        assert len(tools) > 0
        for tool in tools:
            assert callable(tool)

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
    def test_repr(self, agent_cls: type[BaseAgent]) -> None:
        """repr should contain the agent name."""
        agent = agent_cls()
        assert agent.name in repr(agent)


# ---------------------------------------------------------------------------
# build_maf_agent()
# ---------------------------------------------------------------------------


class TestBuildMafAgent:
    """Verify build_maf_agent() constructs an Agent correctly."""

    @pytest.mark.parametrize(
        "agent_cls",
        [AnalyzerAgent, PlannerAgent, TransformerAgent, ValidatorAgent, RepairAdvisorAgent],
    )
    def test_build_maf_agent_returns_agent(self, agent_cls: type[BaseAgent]) -> None:
        """build_maf_agent should return an Agent-like object with name, instructions, and tools."""
        agent = agent_cls()

        # We use a mock client since we don't need a real LLM connection.
        # The Agent constructor should store the client and tools.
        class _MockClient:
            pass

        try:
            maf_agent = agent.build_maf_agent(_MockClient())
            # If agent_framework is installed, verify the agent was built
            assert maf_agent is not None
        except ImportError:
            # agent_framework not installed — verify tools are returned
            tools = agent._get_tools()  # noqa: SLF001
            assert len(tools) > 0

    def test_analyzer_tools_contain_analyze_function(self) -> None:
        """AnalyzerAgent tools should include analyze_mule_input."""
        agent = AnalyzerAgent()
        tools = agent._get_tools()  # noqa: SLF001
        tool_names = [t.__name__ for t in tools]
        assert "analyze_mule_input" in tool_names

    def test_planner_tools_contain_plan_function(self) -> None:
        """PlannerAgent tools should include create_migration_plan."""
        agent = PlannerAgent()
        tools = agent._get_tools()  # noqa: SLF001
        tool_names = [t.__name__ for t in tools]
        assert "create_migration_plan" in tool_names

    def test_transformer_tools_contain_transform_function(self) -> None:
        """TransformerAgent tools should include transform_to_logic_apps."""
        agent = TransformerAgent()
        tools = agent._get_tools()  # noqa: SLF001
        tool_names = [t.__name__ for t in tools]
        assert "transform_to_logic_apps" in tool_names

    def test_validator_tools_contain_validate_function(self) -> None:
        """ValidatorAgent tools should include validate_output_artifacts."""
        agent = ValidatorAgent()
        tools = agent._get_tools()  # noqa: SLF001
        tool_names = [t.__name__ for t in tools]
        assert "validate_output_artifacts" in tool_names

    def test_repair_tools_contain_suggest_function(self) -> None:
        """RepairAdvisorAgent tools should include suggest_repairs."""
        agent = RepairAdvisorAgent()
        tools = agent._get_tools()  # noqa: SLF001
        tool_names = [t.__name__ for t in tools]
        assert "suggest_repairs" in tool_names


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

        class _MockClient:
            pass

        mock_client = _MockClient()
        orchestrator = MigrationOrchestrator(client=mock_client)
        assert orchestrator.client is mock_client

    def test_config_defaults(self) -> None:
        orchestrator = MigrationOrchestrator()
        assert orchestrator.config.endpoint is None
        assert orchestrator.config.model == "gpt-4o"

    def test_custom_config(self) -> None:
        config = FoundryClientConfig(model="gpt-4o-mini")
        orchestrator = MigrationOrchestrator(config=config)
        assert orchestrator.config.model == "gpt-4o-mini"

    def test_offline_run_uses_execute(self, standalone_flow_xml: Path) -> None:
        """In offline mode, the orchestrator should call agent.execute()."""
        orchestrator = MigrationOrchestrator(include_repair=True)
        result = orchestrator.run(str(standalone_flow_xml))

        # Should complete (same as existing tests)
        assert result.overall_status in (AgentStatus.SUCCESS, AgentStatus.PARTIAL)
        assert len(result.steps) >= 4


# ---------------------------------------------------------------------------
# Offline orchestration with stub agents
# ---------------------------------------------------------------------------


class TestOfflineOrchestration:
    """Verify the offline orchestration path with stub agents."""

    def test_offline_pipeline_completes(self) -> None:
        """Offline pipeline with stub agents should complete successfully."""

        class _StubAgent(BaseAgent):
            def __init__(self, name: str = "StubAgent") -> None:
                super().__init__(name=name)

            def _get_tools(self) -> Sequence[Callable[..., Any]]:
                return []

            def execute(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.SUCCESS,
                    output={"stub": True},
                    reasoning_summary="Stub completed",
                    duration_ms=1.0,
                )

        orchestrator = MigrationOrchestrator(
            agents=[_StubAgent("Agent1"), _StubAgent("Agent2")],
        )
        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.SUCCESS
        assert len(result.steps) == 2

    def test_offline_with_correlation_id(self) -> None:
        """Correlation ID should be propagated in offline mode."""

        class _StubAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__(name="StubAgent")

            def _get_tools(self) -> Sequence[Callable[..., Any]]:
                return []

            def execute(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.SUCCESS,
                    output={},
                    reasoning_summary="Done",
                    duration_ms=1.0,
                )

        orchestrator = MigrationOrchestrator(agents=[_StubAgent()])
        result = orchestrator.run("/fake/path", correlation_id="my-cid-999")

        assert result.correlation_id == "my-cid-999"


# ---------------------------------------------------------------------------
# Function tool wrappers
# ---------------------------------------------------------------------------


class TestFunctionToolWrappers:
    """Verify that function_tools functions produce valid JSON."""

    def test_analyze_mule_input(self, standalone_flow_xml: Path) -> None:
        result_str = analyze_mule_input(str(standalone_flow_xml))
        data = json.loads(result_str)

        assert "flow_count" in data
        assert "subflow_count" in data
        assert "construct_count" in data
        assert "warnings" in data
        assert "mode" in data
        assert "validation_valid" in data

    def test_analyze_mule_input_with_mode(self, standalone_flow_xml: Path) -> None:
        result_str = analyze_mule_input(str(standalone_flow_xml), mode="single_flow")
        data = json.loads(result_str)

        assert data["mode"] == "single_flow"

    def test_create_migration_plan(self) -> None:
        ir_json = json.dumps({"construct_names": ["http_listener", "logger"], "flow_count": 1})
        result_str = create_migration_plan(ir_json)
        data = json.loads(result_str)

        assert "flow_count" in data
        assert "construct_summary" in data
        assert "supported_count" in data
        assert "unsupported_count" in data
        assert "mapping_decisions" in data

    def test_transform_to_logic_apps(self) -> None:
        ir_json = json.dumps({"flow_count": 2})
        result_str = transform_to_logic_apps(ir_json, mode="project", output_directory="/tmp/out")  # noqa: S108
        data = json.loads(result_str)

        assert data["mode"] == "project"
        assert data["flow_count"] == 2

    def test_suggest_repairs(self) -> None:
        issues_json = json.dumps([{"rule_id": "OUT_001", "message": "Bad schema", "severity": "error"}])
        gaps_json = json.dumps([{"category": "unsupported_construct", "construct_name": "scatter-gather"}])
        result_str = suggest_repairs(issues_json, gaps_json)
        data = json.loads(result_str)

        assert isinstance(data, list)
        assert len(data) == 2

    def test_functions_are_callable(self) -> None:
        """Verify that tool functions are plain callables suitable for MAF registration."""
        for fn in (analyze_mule_input, create_migration_plan, transform_to_logic_apps, suggest_repairs):
            assert callable(fn)
            assert hasattr(fn, "__name__")
