"""Tests for mule2logic_agent.core.prompt."""

from mule2logic_agent.core.prompt import SYSTEM_PROMPT, build_prompt, build_report_prompt


class TestSystemPrompt:
    def test_is_non_empty_string(self):
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    def test_contains_azure(self):
        assert "Azure" in SYSTEM_PROMPT

    def test_contains_json(self):
        assert "JSON" in SYSTEM_PROMPT


class TestBuildPrompt:
    XML = '<flow name="test"><http:listener path="/hello"/></flow>'

    def test_includes_xml(self):
        result = build_prompt(self.XML)
        assert self.XML in result

    def test_includes_json_instruction(self):
        result = build_prompt(self.XML)
        assert "ONLY" in result and "JSON" in result


class TestBuildReportPrompt:
    XML = '<flow name="test"><set-payload value="Hello"/></flow>'
    WORKFLOW = '{"definition": {"triggers": {}, "actions": {}}}'

    def test_includes_xml(self):
        result = build_report_prompt(self.XML, self.WORKFLOW)
        assert self.XML in result

    def test_includes_workflow_json(self):
        result = build_report_prompt(self.XML, self.WORKFLOW)
        assert "definition" in result
