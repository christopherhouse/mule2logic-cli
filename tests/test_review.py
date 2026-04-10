"""Tests for mule2logic_agent.core.review — uses mocks."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from mule2logic_agent.core.review import review_workflow

VALID_WORKFLOW = {
    "definition": {
        "triggers": {"manual": {"type": "Request", "kind": "Http"}},
        "actions": {"Compose": {"type": "Compose", "inputs": "Hello"}},
    }
}

VALID_JSON = json.dumps(VALID_WORKFLOW)


@pytest.mark.asyncio
class TestReviewWorkflow:
    @patch("mule2logic_agent.core.review.run_agent", new_callable=AsyncMock)
    async def test_returns_reviewed_workflow(self, mock_run):
        mock_run.return_value = VALID_JSON
        xml = '<flow name="test"><http:listener path="/hello"/><set-payload value="Hello"/></flow>'
        workflow, issues = await review_workflow(xml, VALID_WORKFLOW)
        assert workflow["definition"] is not None
        assert workflow["definition"]["actions"] is not None

    @patch("mule2logic_agent.core.review.run_agent", new_callable=AsyncMock)
    async def test_uses_review_system_prompt(self, mock_run):
        mock_run.return_value = VALID_JSON
        xml = '<flow name="test"><set-payload value="Hello"/></flow>'
        await review_workflow(xml, VALID_WORKFLOW)

        call_kwargs = mock_run.call_args.kwargs
        assert "validator" in call_kwargs["system_prompt"].lower() or \
               "review" in call_kwargs["system_prompt"].lower()

    @patch("mule2logic_agent.core.review.run_agent", new_callable=AsyncMock)
    async def test_reports_structural_issues(self, mock_run):
        bad_workflow = json.dumps(
            {
                "definition": {
                    "triggers": {},
                    "actions": {"Bad": {"inputs": "x"}},
                }
            }
        )
        mock_run.return_value = bad_workflow
        xml = '<flow name="test"><set-payload value="x"/></flow>'
        _, issues = await review_workflow(xml, VALID_WORKFLOW)
        assert len(issues) > 0

    @patch("mule2logic_agent.core.review.run_agent", new_callable=AsyncMock)
    async def test_sends_xml_and_workflow_in_prompt(self, mock_run):
        mock_run.return_value = VALID_JSON
        xml = '<flow name="myFlow"><set-payload value="Test"/></flow>'
        await review_workflow(xml, VALID_WORKFLOW)

        prompt = mock_run.call_args.args[0]
        assert "myFlow" in prompt
        assert "Compose" in prompt
