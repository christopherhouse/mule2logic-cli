"""Generates a full Logic Apps Standard project from a MuleIR."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from m2la_contracts.common import MigrationGap
from m2la_ir.enums import ConnectorType
from m2la_ir.models import ConnectorOperation, Flow, MuleIR, Router, Scope

from m2la_transform.models import ProjectArtifacts
from m2la_transform.workflow_generator import generate_workflow

# ── Static artifacts ──────────────────────────────────────────────────────────

_HOST_JSON: dict[str, Any] = {
    "extensionBundle": {
        "id": "Microsoft.Azure.Functions.ExtensionBundle.Workflows",
        "version": "[1.*, 2.0.0)",
    },
    "version": "2.0",
}

_ENV_CONTENT: str = (
    "WORKFLOWS_SUBSCRIPTION_ID=00000000-0000-0000-0000-000000000000\n"
    "WORKFLOWS_RESOURCE_GROUP=rg-placeholder\n"
    "WORKFLOWS_MANAGED_IDENTITY_CLIENT_ID=00000000-0000-0000-0000-000000000000\n"
)

# ── Connector → service-provider mapping ──────────────────────────────────────

# (connection_key, provider_id, display_name)
_CONNECTOR_INFO: dict[ConnectorType, tuple[str, str, str]] = {
    ConnectorType.DB: (
        "sql_connection",
        "/serviceProviders/sql",
        "SQL Connection",
    ),
    ConnectorType.MQ: (
        "servicebus_connection",
        "/serviceProviders/serviceBus",
        "Service Bus Connection",
    ),
    ConnectorType.FTP: (
        "sftp_connection",
        "/serviceProviders/sftp",
        "SFTP Connection",
    ),
    ConnectorType.SFTP: (
        "sftp_connection",
        "/serviceProviders/sftp",
        "SFTP Connection",
    ),
}


def _sanitize_workflow_name(name: str) -> str:
    """Sanitize a flow name for use as a workflow directory name."""
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    sanitized = sanitized.strip("_").lower()
    return sanitized or "workflow"


def _collect_connector_types(flows: list[Flow]) -> set[ConnectorType]:
    """Recursively collect all ConnectorType values referenced in flows."""
    found: set[ConnectorType] = set()

    def _scan(steps: Any) -> None:
        for step in steps:
            if isinstance(step, ConnectorOperation):
                found.add(step.connector_type)
            elif isinstance(step, Scope):
                _scan(step.steps)
            elif isinstance(step, Router):
                for route in step.routes:
                    _scan(route.steps)
                if step.default_route:
                    _scan(step.default_route.steps)

    for flow in flows:
        _scan(flow.steps)
        for handler in flow.error_handlers:
            _scan(handler.steps)

    return found


def _build_connections_json(connector_types: set[ConnectorType]) -> dict[str, Any]:
    """Build connections.json, populating serviceProviderConnections with UAMI auth."""
    service_providers: dict[str, Any] = {}

    for ct in sorted(connector_types):  # sort for determinism
        if ct not in _CONNECTOR_INFO:
            continue
        key, provider_id, display_name = _CONNECTOR_INFO[ct]
        if key in service_providers:
            continue  # already added (FTP and SFTP share a key)
        service_providers[key] = {
            "displayName": display_name,
            "parameterValues": {
                "authProvider": {
                    "Type": "ManagedServiceIdentity",
                }
            },
            "serviceProvider": {
                "id": provider_id,
            },
        }

    return {
        "managedApiConnections": {},
        "serviceProviderConnections": service_providers,
    }


def _build_parameters_json(connector_types: set[ConnectorType]) -> dict[str, Any]:
    """Build parameters.json with the required base keys plus connector-specific entries."""
    params: dict[str, Any] = {
        "WORKFLOWS_RESOURCE_GROUP": {"type": "String", "value": ""},
        "WORKFLOWS_SUBSCRIPTION_ID": {"type": "String", "value": ""},
    }

    for ct in sorted(connector_types):
        if ct not in _CONNECTOR_INFO:
            continue
        conn_key, _, _ = _CONNECTOR_INFO[ct]
        if conn_key not in params:
            params[conn_key] = {"type": "String", "value": ""}

    return params


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write *data* as indented, deterministically sorted JSON to *path*."""
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate_project(
    ir: MuleIR,
    output_dir: Path,
) -> tuple[ProjectArtifacts, list[MigrationGap]]:
    """Generate a complete Logic Apps Standard project from a MuleIR.

    Writes the following files to *output_dir*:

    - ``host.json``
    - ``connections.json``
    - ``parameters.json``
    - ``.env``  (mock/placeholder values only — no real secrets)
    - ``workflows/<name>/workflow.json``  (one per flow)

    Args:
        ir: The intermediate representation of the MuleSoft project.
        output_dir: Root directory where the project files will be written.

    Returns:
        A tuple of (ProjectArtifacts, list[MigrationGap]).
    """
    all_gaps: list[MigrationGap] = []

    # 1. Static host.json (deep-copy to keep _HOST_JSON immutable)
    host_json: dict[str, Any] = dict(_HOST_JSON)

    # 2. Connector discovery → connections.json
    connector_types = _collect_connector_types(ir.flows)
    connections_json = _build_connections_json(connector_types)

    # 3. parameters.json
    parameters_json = _build_parameters_json(connector_types)

    # 4. .env — mock values only
    env_content = _ENV_CONTENT

    # 5. Per-flow workflow generation
    workflows: dict[str, dict[str, Any]] = {}
    for flow in ir.flows:
        workflow_name = _sanitize_workflow_name(flow.name)
        workflow_dict, flow_gaps = generate_workflow(flow)
        all_gaps.extend(flow_gaps)
        workflows[workflow_name] = workflow_dict

    # 6. Write files
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "host.json", host_json)
    _write_json(output_dir / "connections.json", connections_json)
    _write_json(output_dir / "parameters.json", parameters_json)
    (output_dir / ".env").write_text(env_content, encoding="utf-8")

    for workflow_name, workflow_dict in workflows.items():
        wf_dir = output_dir / "workflows" / workflow_name
        wf_dir.mkdir(parents=True, exist_ok=True)
        _write_json(wf_dir / "workflow.json", workflow_dict)

    artifacts = ProjectArtifacts(
        host_json=host_json,
        connections_json=connections_json,
        parameters_json=parameters_json,
        env_content=env_content,
        workflows=workflows,
    )

    return artifacts, all_gaps
