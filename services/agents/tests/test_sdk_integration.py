"""Tests for Microsoft Agent Framework (MAF) integration.

These tests verify:

* ``_get_tools()`` returns the correct tool functions.
* ``build_maf_agent()`` produces a MAF ``Agent`` with tools registered.
* ``MigrationOrchestrator`` requires a chat client.
* ``FoundryClientConfig`` validation.
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

from .mock_chat_client import MockChatClient

# ---------------------------------------------------------------------------
# FoundryClientConfig
# ---------------------------------------------------------------------------


class TestFoundryClientConfig:
    """Verify MAF configuration model."""

    def test_endpoint_required(self) -> None:
        """Omitting endpoint should raise a ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FoundryClientConfig()

    def test_custom_values(self) -> None:
        config = FoundryClientConfig(
            endpoint="https://my-project.api.azureml.ms",
            model="gpt-4o-mini",
        )
        assert config.endpoint == "https://my-project.api.azureml.ms"
        assert config.model == "gpt-4o-mini"

    def test_model_default(self) -> None:
        config = FoundryClientConfig(endpoint="https://example.com")
        assert config.model == "gpt-4o"


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
    def test_build_maf_agent_returns_agent(self, agent_cls: type[BaseAgent], mock_client: MockChatClient) -> None:
        """build_maf_agent should return an Agent-like object with name, instructions, and tools."""
        agent = agent_cls()

        try:
            maf_agent = agent.build_maf_agent(mock_client)
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
# Orchestrator client requirement
# ---------------------------------------------------------------------------


class TestOrchestratorClientRequired:
    """Verify the orchestrator always requires a chat client."""

    def test_client_is_stored(self, mock_client: MockChatClient) -> None:
        """Client should be stored on the orchestrator."""
        orchestrator = MigrationOrchestrator(client=mock_client)
        assert orchestrator.client is mock_client

    def test_run_with_client(self, standalone_flow_xml: Path, mock_client: MockChatClient) -> None:
        """With a client, the orchestrator should execute via the LLM path."""
        orchestrator = MigrationOrchestrator(include_repair=True, client=mock_client)
        result = orchestrator.run(str(standalone_flow_xml))

        assert result.correlation_id
        assert result.total_duration_ms > 0


# ---------------------------------------------------------------------------
# Mock client orchestration with stub agents
# ---------------------------------------------------------------------------


class TestMockClientOrchestration:
    """Verify orchestration with MockChatClient and stub agents."""

    def test_pipeline_completes(self, mock_client: MockChatClient) -> None:
        """Pipeline with stub agents should complete successfully."""

        def _stub_tool() -> str:
            return json.dumps({"stub": True})

        class _StubAgent(BaseAgent):
            def __init__(self, name: str = "StubAgent") -> None:
                super().__init__(name=name)

            def _get_tools(self) -> Sequence[Callable[..., Any]]:
                return [_stub_tool]

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
            client=mock_client,
        )
        result = orchestrator.run("/fake/path")

        assert result.overall_status == AgentStatus.SUCCESS

    def test_correlation_id_propagated(self, mock_client: MockChatClient) -> None:
        """Correlation ID should be propagated."""

        def _stub_tool() -> str:
            return json.dumps({})

        class _StubAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__(name="StubAgent")

            def _get_tools(self) -> Sequence[Callable[..., Any]]:
                return [_stub_tool]

            def execute(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.SUCCESS,
                    output={},
                    reasoning_summary="Done",
                    duration_ms=1.0,
                )

        orchestrator = MigrationOrchestrator(agents=[_StubAgent()], client=mock_client)
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
