"""Tests for mule2logic_agent.core.validate."""

import json
import pytest

from mule2logic_agent.core.validate import validate_json, validate_workflow_structure


VALID_WORKFLOW = {
    "definition": {
        "triggers": {
            "manual": {"type": "Request", "kind": "Http"},
        },
        "actions": {
            "Compose": {"type": "Compose", "inputs": "Hello"},
        },
    }
}

VALID_JSON = json.dumps(VALID_WORKFLOW)


class TestValidateJson:
    def test_parses_valid_json(self):
        result = validate_json(VALID_JSON)
        assert result["definition"]["actions"]["Compose"]["type"] == "Compose"
        assert result["definition"]["triggers"]["manual"]["kind"] == "Http"

    def test_raises_on_non_json(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            validate_json("not json at all")

    def test_raises_on_missing_definition(self):
        with pytest.raises(ValueError, match='Missing required "definition"'):
            validate_json('{"foo": "bar"}')

    def test_raises_on_missing_triggers(self):
        with pytest.raises(ValueError, match='Missing required "definition.triggers"'):
            validate_json('{"definition": {}}')

    def test_raises_on_missing_actions(self):
        with pytest.raises(ValueError, match='Missing required "definition.actions"'):
            validate_json('{"definition": {"triggers": {}}}')

    def test_handles_markdown_code_fences_json(self):
        wrapped = f"```json\n{VALID_JSON}\n```"
        result = validate_json(wrapped)
        assert result["definition"]["actions"]["Compose"]["type"] == "Compose"

    def test_handles_code_fences_no_language(self):
        wrapped = f"```\n{VALID_JSON}\n```"
        result = validate_json(wrapped)
        assert result["definition"]["actions"]["Compose"]["inputs"] == "Hello"

    def test_raises_on_empty_string(self):
        with pytest.raises(ValueError, match="empty"):
            validate_json("")

    def test_raises_on_whitespace_only(self):
        with pytest.raises(ValueError, match="empty"):
            validate_json("   \n  ")

    def test_extracts_json_from_surrounding_text(self):
        text = f"Here is the result:\n{VALID_JSON}\nDone!"
        result = validate_json(text)
        assert result["definition"]["actions"]["Compose"]["type"] == "Compose"


class TestValidateWorkflowStructure:
    def test_returns_empty_for_valid_workflow(self):
        issues = validate_workflow_structure(VALID_WORKFLOW)
        assert issues == []

    def test_detects_missing_triggers(self):
        parsed = {
            "definition": {
                "actions": {"A": {"type": "Compose"}},
            }
        }
        issues = validate_workflow_structure(parsed)
        assert any("triggers" in i for i in issues)

    def test_detects_action_missing_type(self):
        parsed = {
            "definition": {
                "triggers": {},
                "actions": {"BadAction": {"inputs": "test"}},
            }
        }
        issues = validate_workflow_structure(parsed)
        assert any("BadAction" in i and "type" in i for i in issues)

    def test_detects_trigger_missing_type(self):
        parsed = {
            "definition": {
                "triggers": {"badTrigger": {"kind": "Http"}},
                "actions": {"A": {"type": "Compose"}},
            }
        }
        issues = validate_workflow_structure(parsed)
        assert any("badTrigger" in i and "type" in i for i in issues)

    def test_detects_invalid_run_after_references(self):
        parsed = {
            "definition": {
                "triggers": {},
                "actions": {
                    "Step1": {"type": "Compose", "inputs": "x"},
                    "Step2": {
                        "type": "Compose",
                        "inputs": "y",
                        "runAfter": {"NonExistent": ["Succeeded"]},
                    },
                },
            }
        }
        issues = validate_workflow_structure(parsed)
        assert any("NonExistent" in i and "runAfter" in i for i in issues)

    def test_detects_condition_missing_expression(self):
        parsed = {
            "definition": {
                "triggers": {},
                "actions": {"MyCondition": {"type": "If", "actions": {}}},
            }
        }
        issues = validate_workflow_structure(parsed)
        assert any("MyCondition" in i and "expression" in i for i in issues)

    def test_detects_foreach_missing_foreach_input(self):
        parsed = {
            "definition": {
                "triggers": {},
                "actions": {"MyLoop": {"type": "Foreach", "actions": {}}},
            }
        }
        issues = validate_workflow_structure(parsed)
        assert any("MyLoop" in i and "foreach" in i for i in issues)

    def test_detects_foreach_missing_nested_actions(self):
        parsed = {
            "definition": {
                "triggers": {},
                "actions": {
                    "MyLoop": {"type": "Foreach", "foreach": "@triggerBody()"}
                },
            }
        }
        issues = validate_workflow_structure(parsed)
        assert any("MyLoop" in i and "actions" in i for i in issues)
