"""Tests for Logic Apps output integrity validation rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from m2la_contracts.enums import InputMode, Severity, ValidationCategory

from m2la_validate.rules.output_integrity import (
    validate_output,
    validate_project_output,
    validate_single_flow_output,
)

WORKFLOW_SCHEMA = (
    "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
)


def _valid_workflow() -> dict[str, Any]:
    """Return a minimal valid workflow JSON."""
    return {
        "definition": {
            "$schema": WORKFLOW_SCHEMA,
            "contentVersion": "1.0.0.0",
            "triggers": {
                "manual": {
                    "type": "Request",
                    "inputs": {"method": "GET"},
                    "kind": "Http",
                }
            },
            "actions": {
                "Response": {
                    "type": "Response",
                    "inputs": {"statusCode": 200, "body": "OK"},
                    "runAfter": {},
                }
            },
            "outputs": {},
        },
        "kind": "Stateful",
    }


def _create_valid_project(root: Path) -> None:
    """Create a minimal valid Logic Apps Standard project output."""
    root.mkdir(parents=True, exist_ok=True)

    # host.json
    (root / "host.json").write_text(
        json.dumps(
            {
                "version": "2.0",
                "extensionBundle": {
                    "id": "Microsoft.Azure.Functions.ExtensionBundle.Workflows",
                    "version": "[1.*, 2.0.0)",
                },
            },
            indent=2,
        )
    )

    # connections.json
    (root / "connections.json").write_text(
        json.dumps(
            {"managedApiConnections": {}, "serviceProviderConnections": {}},
            indent=2,
        )
    )

    # parameters.json
    (root / "parameters.json").write_text(json.dumps({}, indent=2))

    # .env
    (root / ".env").write_text(
        "WORKFLOWS_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000000\n"
        "WORKFLOWS_RESOURCE_GROUP=rg-placeholder\n"
        "WORKFLOWS_MANAGED_IDENTITY_CLIENT_ID=00000000-0000-0000-0000-000000000000\n"
    )

    # workflows/
    wf_dir = root / "workflows" / "test_flow"
    wf_dir.mkdir(parents=True)
    (wf_dir / "workflow.json").write_text(json.dumps(_valid_workflow(), indent=2))


# ── Project mode: passing cases ──────────────────────────────────────────────


class TestProjectOutputPassing:
    """Project output cases that should produce no errors."""

    def test_valid_project(self, tmp_path: Path) -> None:
        """A complete project should produce no error issues."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        issues = validate_project_output(output_dir)
        errors = [i for i in issues if i.severity in (Severity.ERROR, Severity.CRITICAL)]
        assert errors == []

    def test_no_managed_connectors_no_warnings(self, tmp_path: Path) -> None:
        """No managed connectors should produce no connector warnings."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        issues = validate_project_output(output_dir)
        connector_warns = [i for i in issues if i.category == ValidationCategory.CONNECTOR_PREFERENCE]
        assert connector_warns == []


# ── Project mode: failing cases ──────────────────────────────────────────────


class TestProjectOutputFailing:
    """Project output cases that should produce issues."""

    def test_missing_host_json(self, tmp_path: Path) -> None:
        """Missing host.json should produce an error."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        (output_dir / "host.json").unlink()
        issues = validate_project_output(output_dir)
        rule_ids = [i.rule_id for i in issues]
        assert "OUT_001" in rule_ids

    def test_missing_connections_json(self, tmp_path: Path) -> None:
        """Missing connections.json should produce an error."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        (output_dir / "connections.json").unlink()
        issues = validate_project_output(output_dir)
        has_missing = any(i.rule_id == "OUT_001" and "connections.json" in i.message for i in issues)
        assert has_missing

    def test_missing_env_file(self, tmp_path: Path) -> None:
        """Missing .env should produce an error."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        (output_dir / ".env").unlink()
        issues = validate_project_output(output_dir)
        has_missing = any(i.rule_id == "OUT_001" and ".env" in i.message for i in issues)
        assert has_missing

    def test_missing_workflows_dir(self, tmp_path: Path) -> None:
        """Missing workflows/ directory should produce an error."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        import shutil

        shutil.rmtree(output_dir / "workflows")
        issues = validate_project_output(output_dir)
        rule_ids = [i.rule_id for i in issues]
        assert "OUT_002" in rule_ids

    def test_empty_workflows_dir(self, tmp_path: Path) -> None:
        """Empty workflows/ directory should produce a warning."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        import shutil

        shutil.rmtree(output_dir / "workflows")
        (output_dir / "workflows").mkdir()
        issues = validate_project_output(output_dir)
        rule_ids = [i.rule_id for i in issues]
        assert "OUT_003" in rule_ids

    def test_missing_workflow_json_in_dir(self, tmp_path: Path) -> None:
        """Workflow dir without workflow.json should produce an error."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        (output_dir / "workflows" / "test_flow" / "workflow.json").unlink()
        issues = validate_project_output(output_dir)
        rule_ids = [i.rule_id for i in issues]
        assert "OUT_004" in rule_ids

    def test_host_json_missing_keys(self, tmp_path: Path) -> None:
        """host.json without required keys should produce errors."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        (output_dir / "host.json").write_text(json.dumps({"foo": "bar"}))
        issues = validate_project_output(output_dir)
        out_010 = [i for i in issues if i.rule_id == "OUT_010"]
        assert len(out_010) >= 1

    def test_host_json_missing_extension_bundle_id(self, tmp_path: Path) -> None:
        """host.json extensionBundle without 'id' should produce an error."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        (output_dir / "host.json").write_text(
            json.dumps({"version": "2.0", "extensionBundle": {"version": "[1.*, 2.0.0)"}})
        )
        issues = validate_project_output(output_dir)
        rule_ids = [i.rule_id for i in issues]
        assert "OUT_011" in rule_ids

    def test_env_missing_placeholder_vars(self, tmp_path: Path) -> None:
        """Missing placeholder env vars should produce warnings."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        (output_dir / ".env").write_text("CUSTOM_VAR=foo\n")
        issues = validate_project_output(output_dir)
        env_issues = [i for i in issues if i.rule_id == "OUT_020"]
        assert len(env_issues) >= 1

    def test_managed_api_connector_warning(self, tmp_path: Path) -> None:
        """Managed API connector should produce a preference warning."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        connections = {
            "managedApiConnections": {
                "salesforce": {
                    "connectionId": "/subscriptions/.../managedApis/salesforce",
                    "connectionName": "salesforce",
                    "api": {"id": "/subscriptions/.../managedApis/salesforce"},
                }
            },
            "serviceProviderConnections": {},
        }
        (output_dir / "connections.json").write_text(json.dumps(connections, indent=2))
        issues = validate_project_output(output_dir)
        connector_warns = [i for i in issues if i.rule_id == "OUT_030"]
        assert len(connector_warns) == 1
        assert connector_warns[0].severity == Severity.WARNING
        assert connector_warns[0].category == ValidationCategory.CONNECTOR_PREFERENCE

    def test_service_provider_without_managed_identity(self, tmp_path: Path) -> None:
        """Service provider connection without UAMI auth should produce a warning."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        connections = {
            "managedApiConnections": {},
            "serviceProviderConnections": {
                "sql": {
                    "displayName": "SQL",
                    "parameterValues": {"authProvider": {"Type": "ApiKey"}},
                    "serviceProvider": {"id": "/serviceProviders/sql"},
                }
            },
        }
        (output_dir / "connections.json").write_text(json.dumps(connections, indent=2))
        issues = validate_project_output(output_dir)
        auth_warns = [i for i in issues if i.rule_id == "OUT_031"]
        assert len(auth_warns) == 1
        assert auth_warns[0].severity == Severity.WARNING

    def test_invalid_json_file(self, tmp_path: Path) -> None:
        """Invalid JSON in a required file should produce an error."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        (output_dir / "host.json").write_text("not-json{{{")
        issues = validate_project_output(output_dir)
        json_issues = [i for i in issues if i.rule_id == "OUT_060"]
        assert len(json_issues) >= 1

    def test_invalid_runafter_reference(self, tmp_path: Path) -> None:
        """Invalid runAfter reference should produce an error."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        workflow = _valid_workflow()
        workflow["definition"]["actions"]["BadAction"] = {
            "type": "Compose",
            "inputs": {},
            "runAfter": {"NonExistentAction": ["Succeeded"]},
        }
        wf_path = output_dir / "workflows" / "test_flow" / "workflow.json"
        wf_path.write_text(json.dumps(workflow, indent=2))
        issues = validate_project_output(output_dir)
        runafter_issues = [i for i in issues if i.rule_id == "OUT_050"]
        assert len(runafter_issues) == 1

    def test_all_issues_have_remediation_hints(self, tmp_path: Path) -> None:
        """All output issues should include remediation hints."""
        issues = validate_project_output(tmp_path)  # nonexistent dir
        assert len(issues) > 0
        for issue in issues:
            assert issue.remediation_hint is not None


# ── Single-flow mode: passing cases ──────────────────────────────────────────


class TestSingleFlowOutputPassing:
    """Single-flow output cases that should produce no issues."""

    def test_valid_workflow(self) -> None:
        """A valid workflow dict should produce no issues."""
        issues = validate_single_flow_output(_valid_workflow())
        assert issues == []


# ── Single-flow mode: failing cases ──────────────────────────────────────────


class TestSingleFlowOutputFailing:
    """Single-flow output cases that should produce issues."""

    def test_missing_definition(self) -> None:
        """Workflow without 'definition' should produce an error."""
        issues = validate_single_flow_output({"kind": "Stateful"})
        rule_ids = [i.rule_id for i in issues]
        assert "OUT_040" in rule_ids

    def test_definition_not_dict(self) -> None:
        """Workflow with non-dict 'definition' should produce an error."""
        issues = validate_single_flow_output({"definition": "not-a-dict"})
        rule_ids = [i.rule_id for i in issues]
        assert "OUT_041" in rule_ids

    def test_missing_schema(self) -> None:
        """Definition without '$schema' should produce a warning."""
        workflow = _valid_workflow()
        del workflow["definition"]["$schema"]
        issues = validate_single_flow_output(workflow)
        rule_ids = [i.rule_id for i in issues]
        assert "OUT_042" in rule_ids

    def test_missing_required_keys(self) -> None:
        """Definition without required keys should produce errors."""
        workflow = {
            "definition": {
                "$schema": WORKFLOW_SCHEMA,
            }
        }
        issues = validate_single_flow_output(workflow)
        out_043 = [i for i in issues if i.rule_id == "OUT_043"]
        missing_keys = {i.location for i in out_043}
        assert "$.definition.triggers" in missing_keys
        assert "$.definition.actions" in missing_keys
        assert "$.definition.contentVersion" in missing_keys

    def test_invalid_runafter(self) -> None:
        """Invalid runAfter reference in single-flow mode should produce an error."""
        workflow = _valid_workflow()
        workflow["definition"]["actions"]["Bad"] = {
            "type": "Compose",
            "inputs": {},
            "runAfter": {"Ghost": ["Succeeded"]},
        }
        issues = validate_single_flow_output(workflow)
        runafter_issues = [i for i in issues if i.rule_id == "OUT_050"]
        assert len(runafter_issues) == 1


# ── Dispatch function tests ──────────────────────────────────────────────────


class TestValidateOutputDispatch:
    """Tests for the validate_output dispatch function."""

    def test_project_mode(self, tmp_path: Path) -> None:
        """Project mode should dispatch to project output validator."""
        output_dir = tmp_path / "output"
        _create_valid_project(output_dir)
        issues = validate_output(output_dir, InputMode.PROJECT)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    def test_single_flow_mode(self) -> None:
        """Single-flow mode should dispatch to single-flow output validator."""
        issues = validate_output(_valid_workflow(), InputMode.SINGLE_FLOW)
        assert issues == []

    def test_project_mode_requires_path(self) -> None:
        """Project mode with a dict should raise TypeError."""
        with pytest.raises(TypeError):
            validate_output({}, InputMode.PROJECT)

    def test_single_flow_mode_requires_dict(self) -> None:
        """Single-flow mode with a Path should raise TypeError."""
        with pytest.raises(TypeError):
            validate_output(Path("/tmp"), InputMode.SINGLE_FLOW)
