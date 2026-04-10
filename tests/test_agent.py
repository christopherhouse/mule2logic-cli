"""Tests for mule2logic_agent.core.agent — uses mocks, no real Foundry calls."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mule2logic_agent.core.agent import run_agent

MOCK_JSON = json.dumps(
    {
        "definition": {
            "triggers": {"manual": {"type": "Request", "kind": "Http"}},
            "actions": {"Compose": {"type": "Compose", "inputs": "Hello"}},
        }
    }
)


class _FakeResult:
    """Mimics the Agent.run() return value."""

    def __init__(self, text: str):
        self.text = text


def _make_mock_agent(response_text: str = MOCK_JSON):
    """Create a mocked Agent that returns *response_text* from .run()."""
    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value=_FakeResult(response_text))
    # Support async context manager
    mock_agent.__aenter__ = AsyncMock(return_value=mock_agent)
    mock_agent.__aexit__ = AsyncMock(return_value=False)
    return mock_agent


def _make_mock_client():
    """Create a mocked FoundryChatClient."""
    mock_client = MagicMock()
    mock_client.get_mcp_tool = MagicMock(return_value=MagicMock())
    return mock_client


def _make_mock_credential():
    """Create a mocked AzureCliCredential."""
    mock_cred = AsyncMock()
    mock_cred.__aenter__ = AsyncMock(return_value=mock_cred)
    mock_cred.__aexit__ = AsyncMock(return_value=False)
    return mock_cred


@pytest.mark.asyncio
class TestRunAgent:
    @patch.dict("os.environ", {"FOUNDRY_PROJECT_ENDPOINT": "https://fake.endpoint"})
    @patch("mule2logic_agent.core.agent.AzureCliCredential")
    @patch("mule2logic_agent.core.agent.Agent")
    @patch("mule2logic_agent.core.agent.FoundryChatClient")
    async def test_returns_response_text(
        self, MockClient, MockAgent, MockCredential
    ):
        MockCredential.return_value = _make_mock_credential()
        MockClient.return_value = _make_mock_client()
        MockAgent.return_value = _make_mock_agent()

        result = await run_agent(
            "Convert this XML",
            system_prompt="You are a test agent.",
        )
        assert result == MOCK_JSON

    @patch.dict("os.environ", {"FOUNDRY_PROJECT_ENDPOINT": "https://fake.endpoint"})
    @patch("mule2logic_agent.core.agent.AzureCliCredential")
    @patch("mule2logic_agent.core.agent.Agent")
    @patch("mule2logic_agent.core.agent.FoundryChatClient")
    async def test_creates_mcp_tools(
        self, MockClient, MockAgent, MockCredential
    ):
        mock_client = _make_mock_client()
        MockCredential.return_value = _make_mock_credential()
        MockClient.return_value = mock_client
        MockAgent.return_value = _make_mock_agent()

        await run_agent(
            "test prompt",
            system_prompt="You are a test agent.",
        )

        # Verify both MCP tools were created
        calls = mock_client.get_mcp_tool.call_args_list
        assert len(calls) == 2
        urls = {call.kwargs.get("url") or call[1].get("url", "") for call in calls}
        assert "https://learn.microsoft.com/api/mcp" in urls
        assert "https://mcp.context7.com/mcp" in urls

    @patch.dict("os.environ", {}, clear=True)
    async def test_raises_without_endpoint(self):
        with pytest.raises(RuntimeError, match="FOUNDRY_PROJECT_ENDPOINT"):
            await run_agent(
                "test",
                system_prompt="test",
            )

    @patch.dict("os.environ", {"FOUNDRY_PROJECT_ENDPOINT": "https://fake.endpoint"})
    @patch("mule2logic_agent.core.agent.AzureCliCredential")
    @patch("mule2logic_agent.core.agent.Agent")
    @patch("mule2logic_agent.core.agent.FoundryChatClient")
    async def test_passes_model_and_instructions(
        self, MockClient, MockAgent, MockCredential
    ):
        MockCredential.return_value = _make_mock_credential()
        MockClient.return_value = _make_mock_client()
        mock_agent = _make_mock_agent()
        MockAgent.return_value = mock_agent

        await run_agent(
            "test prompt",
            system_prompt="Custom instructions here",
            model="gpt-4o-mini",
        )

        # Verify Agent was constructed with the right instructions
        agent_kwargs = MockAgent.call_args.kwargs
        assert agent_kwargs["instructions"] == "Custom instructions here"
        assert agent_kwargs["name"] == "MuleSoftConverter"
