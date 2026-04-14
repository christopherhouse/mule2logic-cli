"""Logic Apps output integrity validation rules.

Validates generated Logic Apps Standard project artifacts and standalone workflow JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from m2la_contracts.enums import InputMode, Severity, ValidationCategory
from m2la_contracts.validate import ValidationIssue

WORKFLOW_SCHEMA = (
    "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
)

# Required top-level files in a Logic Apps Standard project
_PROJECT_REQUIRED_FILES = ["host.json", "connections.json", "parameters.json", ".env"]

# Required keys in host.json
_HOST_REQUIRED_KEYS = {"version", "extensionBundle"}

# Expected .env placeholder variables
_EXPECTED_ENV_VARS = {
    "WORKFLOWS_SUBSCRIPTION_ID",
    "WORKFLOWS_RESOURCE_GROUP",
    "WORKFLOWS_MANAGED_IDENTITY_CLIENT_ID",
}


def validate_project_output(output_dir: Path) -> list[ValidationIssue]:
    """Validate a full Logic Apps Standard project output directory.

    Checks:
    - Required files exist (host.json, connections.json, parameters.json, .env)
    - host.json has required structure
    - connections.json is valid JSON with expected structure
    - parameters.json is valid JSON
    - .env contains required placeholder variables
    - At least one workflow exists in workflows/ directory
    - Each workflow.json is structurally valid
    - Connector preference warnings
    """
    issues: list[ValidationIssue] = []

    # Check required files
    for filename in _PROJECT_REQUIRED_FILES:
        filepath = output_dir / filename
        if not filepath.is_file():
            issues.append(
                ValidationIssue(
                    rule_id="OUT_001",
                    message=f"Missing required file: {filename}",
                    severity=Severity.ERROR,
                    category=ValidationCategory.OUTPUT_INTEGRITY,
                    artifact_path=str(filepath),
                    remediation_hint=f"Generate the {filename} file in the output directory.",
                )
            )

    # Validate host.json
    _validate_host_json(output_dir / "host.json", issues)

    # Validate connections.json
    _validate_connections_json(output_dir / "connections.json", issues)

    # Validate parameters.json
    _load_json_file(output_dir / "parameters.json", "parameters.json", issues)

    # Validate .env
    _validate_env_file(output_dir / ".env", issues)

    # Validate workflows directory
    workflows_dir = output_dir / "workflows"
    if not workflows_dir.is_dir():
        issues.append(
            ValidationIssue(
                rule_id="OUT_002",
                message="Missing workflows/ directory",
                severity=Severity.ERROR,
                category=ValidationCategory.OUTPUT_INTEGRITY,
                artifact_path=str(workflows_dir),
                remediation_hint="Generate at least one workflow in the workflows/ directory.",
            )
        )
    else:
        workflow_dirs = [d for d in workflows_dir.iterdir() if d.is_dir()]
        if not workflow_dirs:
            issues.append(
                ValidationIssue(
                    rule_id="OUT_003",
                    message="No workflow directories found in workflows/",
                    severity=Severity.WARNING,
                    category=ValidationCategory.OUTPUT_INTEGRITY,
                    artifact_path=str(workflows_dir),
                    remediation_hint="Ensure at least one workflow was generated.",
                )
            )
        for wf_dir in workflow_dirs:
            wf_json = wf_dir / "workflow.json"
            if not wf_json.is_file():
                issues.append(
                    ValidationIssue(
                        rule_id="OUT_004",
                        message=f"Missing workflow.json in {wf_dir.name}/",
                        severity=Severity.ERROR,
                        category=ValidationCategory.OUTPUT_INTEGRITY,
                        artifact_path=str(wf_json),
                        remediation_hint=f"Generate workflow.json for the '{wf_dir.name}' workflow.",
                    )
                )
            else:
                _validate_workflow_json(wf_json, issues)

    return issues


def validate_single_flow_output(workflow_json: dict[str, Any]) -> list[ValidationIssue]:
    """Validate a standalone workflow JSON dict (single-flow mode).

    Checks:
    - Has 'definition' key
    - Definition has required schema, triggers, actions, contentVersion
    - runAfter references are valid
    """
    issues: list[ValidationIssue] = []
    _validate_workflow_dict(workflow_json, "workflow.json", issues)
    return issues


def _validate_host_json(path: Path, issues: list[ValidationIssue]) -> None:
    """Validate host.json structure."""
    data = _load_json_file(path, "host.json", issues)
    if data is None:
        return

    for key in _HOST_REQUIRED_KEYS:
        if key not in data:
            issues.append(
                ValidationIssue(
                    rule_id="OUT_010",
                    message=f"host.json missing required key: '{key}'",
                    severity=Severity.ERROR,
                    category=ValidationCategory.OUTPUT_INTEGRITY,
                    artifact_path=str(path),
                    location=f"$.{key}",
                    remediation_hint=f"Add the '{key}' key to host.json.",
                )
            )

    ext_bundle = data.get("extensionBundle")
    if isinstance(ext_bundle, dict):
        if "id" not in ext_bundle:
            issues.append(
                ValidationIssue(
                    rule_id="OUT_011",
                    message="host.json extensionBundle missing 'id'",
                    severity=Severity.ERROR,
                    category=ValidationCategory.OUTPUT_INTEGRITY,
                    artifact_path=str(path),
                    location="$.extensionBundle.id",
                    remediation_hint=(
                        "Add 'id' to extensionBundle (e.g., 'Microsoft.Azure.Functions.ExtensionBundle.Workflows')."
                    ),
                )
            )


def _validate_connections_json(path: Path, issues: list[ValidationIssue]) -> None:
    """Validate connections.json structure and connector preferences."""
    data = _load_json_file(path, "connections.json", issues)
    if data is None:
        return

    # Check for managed API connections — warn if they exist (should prefer built-in)
    managed = data.get("managedApiConnections", {})
    if managed:
        for conn_name, conn_config in managed.items():
            issues.append(
                ValidationIssue(
                    rule_id="OUT_030",
                    message=(
                        f"Managed API connector '{conn_name}' used; prefer built-in connector with identity-based auth"
                    ),
                    severity=Severity.WARNING,
                    category=ValidationCategory.CONNECTOR_PREFERENCE,
                    artifact_path=str(path),
                    location=f"$.managedApiConnections.{conn_name}",
                    remediation_hint=(
                        f"Consider replacing managed connector '{conn_name}' with a built-in "
                        "serviceProviderConnection using managed identity authentication."
                    ),
                )
            )

    # Validate service provider connections have auth configured
    sp_conns = data.get("serviceProviderConnections", {})
    for conn_name, conn_config in sp_conns.items():
        if not isinstance(conn_config, dict):
            continue
        param_values = conn_config.get("parameterValues", {})
        auth_provider = param_values.get("authProvider", {})
        auth_type = auth_provider.get("Type", "") if isinstance(auth_provider, dict) else ""
        if auth_type != "ManagedServiceIdentity":
            issues.append(
                ValidationIssue(
                    rule_id="OUT_031",
                    message=f"Service provider connection '{conn_name}' does not use managed identity auth",
                    severity=Severity.WARNING,
                    category=ValidationCategory.CONNECTOR_PREFERENCE,
                    artifact_path=str(path),
                    location=f"$.serviceProviderConnections.{conn_name}.parameterValues.authProvider",
                    remediation_hint=(
                        f"Configure '{conn_name}' to use ManagedServiceIdentity authentication. "
                        "Identity-based auth is preferred per spec §8."
                    ),
                )
            )


def _validate_env_file(path: Path, issues: list[ValidationIssue]) -> None:
    """Validate .env file contains required placeholder variables."""
    if not path.is_file():
        return

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return

    defined_vars: set[str] = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            var_name = line.split("=", 1)[0].strip()
            defined_vars.add(var_name)

    for expected_var in _EXPECTED_ENV_VARS:
        if expected_var not in defined_vars:
            issues.append(
                ValidationIssue(
                    rule_id="OUT_020",
                    message=f"Missing placeholder environment variable: {expected_var}",
                    severity=Severity.WARNING,
                    category=ValidationCategory.OUTPUT_INTEGRITY,
                    artifact_path=str(path),
                    remediation_hint=f"Add '{expected_var}=<placeholder>' to the .env file.",
                )
            )


def _validate_workflow_json(path: Path, issues: list[ValidationIssue]) -> None:
    """Validate a workflow.json file on disk."""
    data = _load_json_file(path, str(path.name), issues)
    if data is None:
        return
    _validate_workflow_dict(data, str(path), issues)


def _validate_workflow_dict(data: dict[str, Any], artifact_id: str, issues: list[ValidationIssue]) -> None:
    """Validate workflow.json structure and references."""
    # Check top-level structure
    if "definition" not in data:
        issues.append(
            ValidationIssue(
                rule_id="OUT_040",
                message="Workflow JSON missing 'definition' key",
                severity=Severity.ERROR,
                category=ValidationCategory.OUTPUT_INTEGRITY,
                artifact_path=artifact_id,
                remediation_hint="Add a 'definition' object to the workflow JSON.",
            )
        )
        return

    defn = data["definition"]
    if not isinstance(defn, dict):
        issues.append(
            ValidationIssue(
                rule_id="OUT_041",
                message="Workflow 'definition' is not a JSON object",
                severity=Severity.ERROR,
                category=ValidationCategory.OUTPUT_INTEGRITY,
                artifact_path=artifact_id,
                remediation_hint="Ensure 'definition' is a valid JSON object.",
            )
        )
        return

    # Check schema
    schema = defn.get("$schema", "")
    if not schema:
        issues.append(
            ValidationIssue(
                rule_id="OUT_042",
                message="Workflow definition missing '$schema'",
                severity=Severity.WARNING,
                category=ValidationCategory.OUTPUT_INTEGRITY,
                artifact_path=artifact_id,
                location="$.definition.$schema",
                remediation_hint=f"Add '$schema': '{WORKFLOW_SCHEMA}' to the definition.",
            )
        )

    # Check required keys
    for key in ("triggers", "actions", "contentVersion"):
        if key not in defn:
            issues.append(
                ValidationIssue(
                    rule_id="OUT_043",
                    message=f"Workflow definition missing '{key}'",
                    severity=Severity.ERROR,
                    category=ValidationCategory.OUTPUT_INTEGRITY,
                    artifact_path=artifact_id,
                    location=f"$.definition.{key}",
                    remediation_hint=f"Add the '{key}' key to the workflow definition.",
                )
            )

    # Validate runAfter references
    actions = defn.get("actions", {})
    if isinstance(actions, dict):
        _validate_run_after_refs(actions, artifact_id, issues)


def _validate_run_after_refs(actions: dict[str, Any], artifact_id: str, issues: list[ValidationIssue]) -> None:
    """Validate that all runAfter references point to existing actions."""
    action_names = set(actions.keys())

    for action_name, action_def in actions.items():
        if not isinstance(action_def, dict):
            continue
        run_after = action_def.get("runAfter", {})
        if not isinstance(run_after, dict):
            continue
        for ref_name in run_after:
            if ref_name not in action_names:
                issues.append(
                    ValidationIssue(
                        rule_id="OUT_050",
                        message=f"Action '{action_name}' has invalid runAfter reference to '{ref_name}'",
                        severity=Severity.ERROR,
                        category=ValidationCategory.OUTPUT_INTEGRITY,
                        artifact_path=artifact_id,
                        location=f"$.definition.actions.{action_name}.runAfter.{ref_name}",
                        remediation_hint=f"Ensure action '{ref_name}' exists or remove it from runAfter.",
                    )
                )

        # Check for nested actions (e.g., in foreach, condition)
        _validate_nested_actions(action_def, action_name, artifact_id, issues)


def _validate_nested_actions(
    action_def: dict[str, Any],
    parent_name: str,
    artifact_id: str,
    issues: list[ValidationIssue],
) -> None:
    """Recursively validate runAfter in nested action structures."""
    # Check 'actions' within scopes like Foreach, Condition branches, etc.
    nested_actions = action_def.get("actions")
    if isinstance(nested_actions, dict) and nested_actions:
        _validate_run_after_refs(nested_actions, artifact_id, issues)

    # Check condition branches (If_True, If_False under "actions" and "else")
    else_block = action_def.get("else")
    if isinstance(else_block, dict):
        else_actions = else_block.get("actions")
        if isinstance(else_actions, dict) and else_actions:
            _validate_run_after_refs(else_actions, artifact_id, issues)


def _load_json_file(path: Path, label: str, issues: list[ValidationIssue]) -> dict[str, Any] | None:
    """Load and parse a JSON file, recording issues if invalid."""
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as e:
        issues.append(
            ValidationIssue(
                rule_id="OUT_060",
                message=f"Invalid JSON in {label}: {e}",
                severity=Severity.ERROR,
                category=ValidationCategory.OUTPUT_INTEGRITY,
                artifact_path=str(path),
                remediation_hint=f"Fix the JSON syntax in {label}.",
            )
        )
        return None
    except OSError as e:
        issues.append(
            ValidationIssue(
                rule_id="OUT_061",
                message=f"Cannot read {label}: {e}",
                severity=Severity.ERROR,
                category=ValidationCategory.OUTPUT_INTEGRITY,
                artifact_path=str(path),
                remediation_hint=f"Ensure {label} is readable.",
            )
        )
        return None


def validate_output(
    output: Path | dict[str, Any],
    mode: InputMode,
) -> list[ValidationIssue]:
    """Dispatch to the appropriate output validator based on mode."""
    if mode == InputMode.PROJECT:
        if not isinstance(output, Path):
            raise TypeError("Project mode requires a Path to the output directory")
        return validate_project_output(output)
    if isinstance(output, dict):
        return validate_single_flow_output(output)
    raise TypeError("Single-flow mode requires a workflow JSON dict")
