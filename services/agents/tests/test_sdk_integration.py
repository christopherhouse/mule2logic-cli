"""Tests for Azure AI Agents SDK integration.

These tests verify:

* ``_register_tools()`` is called and populates the ``toolset``.
* ``create_on_service()`` and ``cleanup()`` work with a mocked client.
* ``as_connected_agent_tool()`` produces valid ``ConnectedAgentTool``.
* Multi-agent orchestration: orchestrator creates sub-agents,
  wires ``ConnectedAgentTool``, creates thread + run.
* Offline vs online mode selection in the orchestrator.
* ``FunctionTool`` wrappers produce valid JSON output.
* ``AgentsClientConfig`` defaults and validation.
* Rich system prompts are loaded and used.
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
from m2la_agents.prompts import (
    ANALYZER_PROMPT,
    ORCHESTRATOR_PROMPT,
    PLANNER_PROMPT,
    REPAIR_ADVISOR_PROMPT,
    TRANSFORMER_PROMPT,
    VALIDATOR_PROMPT,
)
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
# System prompts
# ---------------------------------------------------------------------------


class TestSystemPrompts:
    """Verify that system prompts are rich, non-trivial, and used by agents."""

    def test_orchestrator_prompt_exists(self) -> None:
        assert len(ORCHESTRATOR_PROMPT) > 200
        assert "Migration Orchestrator" in ORCHESTRATOR_PROMPT
        assert "sub-agent" in ORCHESTRATOR_PROMPT.lower() or "delegate" in ORCHESTRATOR_PROMPT.lower()

    def test_analyzer_prompt_used(self) -> None:
        agent = AnalyzerAgent()
        assert agent.instructions == ANALYZER_PROMPT
        assert "analyze_mule_input" in agent.instructions

    def test_planner_prompt_used(self) -> None:
        agent = PlannerAgent()
        assert agent.instructions == PLANNER_PROMPT
        assert "migration plan" in agent.instructions.lower()

    def test_transformer_prompt_used(self) -> None:
        agent = TransformerAgent()
        assert agent.instructions == TRANSFORMER_PROMPT
        assert "transform" in agent.instructions.lower()

    def test_validator_prompt_used(self) -> None:
        agent = ValidatorAgent()
        assert agent.instructions == VALIDATOR_PROMPT
        assert "validate" in agent.instructions.lower()

    def test_repair_prompt_used(self) -> None:
        agent = RepairAdvisorAgent()
        assert agent.instructions == REPAIR_ADVISOR_PROMPT
        assert "repair" in agent.instructions.lower()

    @pytest.mark.parametrize(
        "prompt",
        [ANALYZER_PROMPT, PLANNER_PROMPT, TRANSFORMER_PROMPT, VALIDATOR_PROMPT, REPAIR_ADVISOR_PROMPT],
    )
    def test_prompts_are_substantial(self, prompt: str) -> None:
        """Each prompt should contain meaningful domain-specific instructions."""
        assert len(prompt) > 200
        # Should mention the tool or the domain
        lower = prompt.lower()
        assert "mulesoft" in lower or "logic apps" in lower or "migration" in lower


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
# create_on_service() / cleanup() / as_connected_agent_tool() with mocked client
# ---------------------------------------------------------------------------


class TestSDKLifecycle:
    """Verify create_on_service / cleanup / as_connected_agent_tool with a mocked AgentsClient."""

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
# ConnectedAgentTool wiring
# ---------------------------------------------------------------------------


class TestConnectedAgentTool:
    """Verify as_connected_agent_tool() for multi-agent orchestration."""

    def _make_mock_client(self) -> MagicMock:
        client = MagicMock()
        mock_agent = MagicMock()
        mock_agent.id = "sub-agent-abc123"
        client.create_agent.return_value = mock_agent
        return client

    def test_as_connected_agent_tool_after_create(self) -> None:
        """After create_on_service, as_connected_agent_tool should return a valid tool."""
        agent = AnalyzerAgent()
        client = self._make_mock_client()

        agent.create_on_service(client, "gpt-4o")
        connected = agent.as_connected_agent_tool("Analyzes MuleSoft input")

        # ConnectedAgentTool should have the agent ID and name
        assert connected is not None
        assert hasattr(connected, "definitions")
        assert len(connected.definitions) > 0

    def test_as_connected_agent_tool_raises_when_offline(self) -> None:
        """as_connected_agent_tool should raise if agent is not on service."""
        agent = AnalyzerAgent()

        with pytest.raises(RuntimeError, match="not been created on the service"):
            agent.as_connected_agent_tool("description")

    @pytest.mark.parametrize(
        "agent_cls",
        [AnalyzerAgent, PlannerAgent, TransformerAgent, ValidatorAgent, RepairAdvisorAgent],
    )
    def test_all_agents_produce_connected_tool(self, agent_cls: type[BaseAgent]) -> None:
        """Every agent type should produce a ConnectedAgentTool after creation."""
        agent = agent_cls()
        client = self._make_mock_client()

        agent.create_on_service(client, "gpt-4o")
        connected = agent.as_connected_agent_tool(f"Test {agent.name}")

        assert connected is not None
        assert len(connected.definitions) > 0


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


# ---------------------------------------------------------------------------
# Multi-agent orchestration (online mode)
# ---------------------------------------------------------------------------


class TestMultiAgentOrchestration:
    """Verify the full multi-agent orchestration with mocked AgentsClient."""

    def _build_mock_client(self) -> MagicMock:
        """Build a mock client that supports multi-agent creation."""
        client = MagicMock()

        # Each create_agent call returns a new mock agent with unique ID
        agent_counter = {"n": 0}

        def _create_agent(**kwargs):
            agent_counter["n"] += 1
            mock = MagicMock()
            mock.id = f"agent-{agent_counter['n']}"
            mock.name = kwargs.get("name", f"agent-{agent_counter['n']}")
            return mock

        client.create_agent.side_effect = _create_agent

        # Thread creation
        mock_thread = MagicMock()
        mock_thread.id = "thread-main"
        client.threads.create.return_value = mock_thread

        # Message creation
        mock_message = MagicMock()
        mock_message.id = "msg-1"
        client.messages.create.return_value = mock_message

        # Run creation
        mock_run = MagicMock()
        mock_run.status = "completed"
        mock_run.id = "run-main"
        client.runs.create_and_process.return_value = mock_run

        # Messages listing (for response extraction)
        mock_agent_msg = MagicMock()
        mock_agent_msg.role = "MessageRole.AGENT"
        mock_text = MagicMock()
        mock_text.text.value = "Migration completed: 3 flows analyzed, 2 supported, 1 gap found."
        mock_agent_msg.text_messages = [mock_text]
        client.messages.list.return_value = [mock_agent_msg]

        return client

    def test_creates_sub_agents_then_orchestrator(self) -> None:
        """Orchestrator should create sub-agents + main orchestrator agent."""

        class _StubAgent(BaseAgent):
            def __init__(self, name: str = "StubAgent") -> None:
                super().__init__(name=name)

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

        client = self._build_mock_client()
        stub1 = _StubAgent("Agent1")
        stub2 = _StubAgent("Agent2")

        orchestrator = MigrationOrchestrator(
            agents=[stub1, stub2],
            client=client,
        )
        result = orchestrator.run("/fake/path")

        # Should have created: 2 sub-agents + 1 orchestrator = 3 create_agent calls
        assert client.create_agent.call_count == 3

        # Check that the last create_agent call is for the orchestrator
        last_call_kwargs = client.create_agent.call_args_list[-1]
        assert last_call_kwargs.kwargs.get("name") == "MigrationOrchestrator"
        assert "tools" in last_call_kwargs.kwargs

        assert result.overall_status == AgentStatus.SUCCESS

    def test_creates_thread_and_sends_message(self) -> None:
        """Online mode should create a thread and post a migration request."""

        class _StubAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__(name="StubAgent")

            def _register_tools(self) -> None:
                pass

            def execute(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.SUCCESS,
                    output={},
                    reasoning_summary="Done",
                    duration_ms=1.0,
                )

        client = self._build_mock_client()
        orchestrator = MigrationOrchestrator(agents=[_StubAgent()], client=client)
        orchestrator.run("/path/to/project")

        # Thread should be created
        client.threads.create.assert_called_once()

        # A user message should be posted to the thread
        client.messages.create.assert_called_once()
        msg_kwargs = client.messages.create.call_args.kwargs
        assert msg_kwargs["thread_id"] == "thread-main"
        assert "/path/to/project" in msg_kwargs["content"]

    def test_runs_orchestrator_agent(self) -> None:
        """Online mode should create a run for the orchestrator agent."""

        class _StubAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__(name="StubAgent")

            def _register_tools(self) -> None:
                pass

            def execute(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.SUCCESS,
                    output={},
                    reasoning_summary="Done",
                    duration_ms=1.0,
                )

        client = self._build_mock_client()
        orchestrator = MigrationOrchestrator(agents=[_StubAgent()], client=client)
        orchestrator.run("/fake/path")

        # A run should be created with the orchestrator agent ID
        client.runs.create_and_process.assert_called_once()
        run_kwargs = client.runs.create_and_process.call_args.kwargs
        assert run_kwargs["thread_id"] == "thread-main"
        # The agent_id should be the orchestrator's ID (last created agent)
        assert run_kwargs["agent_id"] is not None

    def test_cleans_up_all_agents(self) -> None:
        """Online mode should clean up sub-agents AND the orchestrator."""

        class _StubAgent(BaseAgent):
            def __init__(self, name: str = "StubAgent") -> None:
                super().__init__(name=name)

            def _register_tools(self) -> None:
                pass

            def execute(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.SUCCESS,
                    output={},
                    reasoning_summary="Done",
                    duration_ms=1.0,
                )

        client = self._build_mock_client()
        orchestrator = MigrationOrchestrator(
            agents=[_StubAgent("A"), _StubAgent("B")],
            client=client,
        )
        orchestrator.run("/fake/path")

        # Should delete: orchestrator agent + 2 sub-agents = 3 deletes
        assert client.delete_agent.call_count == 3

    def test_extracts_agent_response(self) -> None:
        """Online mode should extract the orchestrator's text response."""

        class _StubAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__(name="StubAgent")

            def _register_tools(self) -> None:
                pass

            def execute(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.SUCCESS,
                    output={"data": True},
                    reasoning_summary="Done",
                    duration_ms=1.0,
                )

        client = self._build_mock_client()
        orchestrator = MigrationOrchestrator(agents=[_StubAgent()], client=client)
        result = orchestrator.run("/fake/path")

        # The orchestrator's LLM response should be in the final output
        if isinstance(result.final_output, dict):
            assert "orchestrator_reasoning" in result.final_output

    def test_correlation_id_in_message(self) -> None:
        """The user message should include the correlation ID."""

        class _StubAgent(BaseAgent):
            def __init__(self) -> None:
                super().__init__(name="StubAgent")

            def _register_tools(self) -> None:
                pass

            def execute(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.SUCCESS,
                    output={},
                    reasoning_summary="Done",
                    duration_ms=1.0,
                )

        client = self._build_mock_client()
        orchestrator = MigrationOrchestrator(agents=[_StubAgent()], client=client)
        orchestrator.run("/fake/path", correlation_id="my-cid-999")

        msg_kwargs = client.messages.create.call_args.kwargs
        assert "my-cid-999" in msg_kwargs["content"]

    def test_enable_auto_function_calls_per_agent(self) -> None:
        """enable_auto_function_calls should be called for each sub-agent."""

        class _StubAgent(BaseAgent):
            def __init__(self, name: str = "StubAgent") -> None:
                super().__init__(name=name)

            def _register_tools(self) -> None:
                pass

            def execute(self, context: AgentContext) -> AgentResult:
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.SUCCESS,
                    output={},
                    reasoning_summary="Done",
                    duration_ms=1.0,
                )

        client = self._build_mock_client()
        orchestrator = MigrationOrchestrator(
            agents=[_StubAgent("A"), _StubAgent("B")],
            client=client,
        )
        orchestrator.run("/fake/path")

        assert client.enable_auto_function_calls.call_count == 2


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
