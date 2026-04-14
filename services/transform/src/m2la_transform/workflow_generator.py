"""Converts a single IR Flow into a Logic Apps Standard workflow.json dict."""

from __future__ import annotations

import re
from typing import Any

from m2la_contracts.common import MigrationGap
from m2la_contracts.enums import GapCategory, Severity
from m2la_ir.enums import ConnectorType, ProcessorType, RouterType, ScopeType, TriggerType
from m2la_ir.models import ConnectorOperation, Flow, FlowStep, Processor, Router, Scope, Transform, VariableOperation

WORKFLOW_SCHEMA = (
    "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
)

# Map MuleSoft time units to Logic Apps recurrence frequency strings
_TIME_UNIT_MAP: dict[str, str] = {
    "MILLISECONDS": "Second",
    "SECONDS": "Second",
    "MINUTES": "Minute",
    "HOURS": "Hour",
    "DAYS": "Day",
    "WEEKS": "Week",
    "MONTHS": "Month",
}


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use as a Logic Apps action or workflow key."""
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    sanitized = sanitized.strip("_").lower()
    return sanitized or "step"


def _source_location_str(step: Any) -> str:
    """Extract a human-readable source location string from a step."""
    if hasattr(step, "source_location") and step.source_location is not None:
        loc = step.source_location
        return f"{loc.file}:{loc.line or '?'}"
    return "unknown"


def _make_gap(
    construct_name: str,
    source_location: str,
    message: str,
    category: GapCategory = GapCategory.UNSUPPORTED_CONSTRUCT,
    severity: Severity = Severity.WARNING,
    suggested_workaround: str | None = None,
) -> MigrationGap:
    """Construct a MigrationGap with consistent defaults."""
    return MigrationGap(
        construct_name=construct_name,
        source_location=source_location,
        category=category,
        severity=severity,
        message=message,
        suggested_workaround=suggested_workaround,
    )


def _map_scheduler_frequency(frequency: str, time_unit: str) -> tuple[str, int]:
    """Convert MuleSoft scheduler frequency/timeUnit to Logic Apps recurrence params."""
    try:
        interval = int(frequency)
    except (ValueError, TypeError):
        interval = 1

    la_frequency = _TIME_UNIT_MAP.get(time_unit.upper(), "Minute")

    if time_unit.upper() == "MILLISECONDS":
        # Convert ms → seconds, minimum 1
        interval = max(1, interval // 1000)

    return la_frequency, interval


def _map_trigger(
    flow: Flow,
) -> tuple[dict[str, Any], str, list[MigrationGap]]:
    """Map a Flow trigger to a Logic Apps triggers dict.

    Returns:
        A tuple of (triggers_dict, trigger_key, gaps).
        trigger_key is empty string when there is no trigger.
    """
    gaps: list[MigrationGap] = []

    if flow.trigger is None:
        return {}, "", gaps

    trigger = flow.trigger
    src = _source_location_str(trigger)

    if trigger.type == TriggerType.HTTP_LISTENER:
        trigger_def: dict[str, Any] = {
            "type": "Request",
            "kind": "Http",
            "inputs": {"schema": {}},
            "operationOptions": "EnableSchemaValidation",
        }
        # Carry over method hint if present
        if "method" in trigger.config:
            trigger_def["inputs"]["method"] = trigger.config["method"]
        return {"manual": trigger_def}, "manual", gaps

    if trigger.type == TriggerType.SCHEDULER:
        config = trigger.config
        frequency = str(config.get("frequency", "1"))
        time_unit = str(config.get("timeUnit", "MINUTES"))
        la_frequency, interval = _map_scheduler_frequency(frequency, time_unit)
        trigger_def = {
            "type": "Recurrence",
            "recurrence": {
                "frequency": la_frequency,
                "interval": interval,
            },
        }
        return {"Recurrence": trigger_def}, "Recurrence", gaps

    # Unknown trigger — emit a gap and fall back to a placeholder Request trigger
    gaps.append(
        _make_gap(
            construct_name=f"trigger:{trigger.type}",
            source_location=src,
            message=(
                f"Trigger type '{trigger.type}' has no direct Logic Apps equivalent. Manual implementation required."
            ),
            category=GapCategory.UNSUPPORTED_CONSTRUCT,
            severity=Severity.ERROR,
            suggested_workaround=(
                "Replace with a supported trigger (Request or Recurrence) in the generated workflow."
            ),
        )
    )
    placeholder: dict[str, Any] = {
        "type": "Request",
        "kind": "Http",
        "inputs": {"schema": {}},
        "description": f"MIGRATION GAP: trigger type '{trigger.type}' is not supported.",
    }
    return {"manual": placeholder}, "manual", gaps


def _map_connector_operation(
    step: ConnectorOperation,
) -> tuple[dict[str, Any], list[MigrationGap]]:
    """Map a ConnectorOperation to a Logic Apps action body (without runAfter)."""
    gaps: list[MigrationGap] = []
    config = step.config
    src = _source_location_str(step)

    if step.connector_type == ConnectorType.HTTP_REQUEST:
        action: dict[str, Any] = {
            "type": "Http",
            "inputs": {
                "method": config.get("method", "GET"),
                "uri": config.get("url", ""),
            },
        }
        return action, gaps

    if step.connector_type == ConnectorType.DB:
        action = {
            "type": "ApiConnection",
            "inputs": {
                "host": {"connection": {"name": "@parameters('sql_connection')"}},
                "method": "post",
                "path": "/datasets/default/query/sql",
                "body": {"query": config.get("query", "")},
            },
        }
        return action, gaps

    if step.connector_type == ConnectorType.MQ:
        action = {
            "type": "ApiConnection",
            "inputs": {
                "host": {"connection": {"name": "@parameters('servicebus_connection')"}},
                "method": "post",
                "path": "/topics/publish/message",
            },
        }
        return action, gaps

    if step.connector_type in (ConnectorType.FTP, ConnectorType.SFTP):
        action = {
            "type": "ApiConnection",
            "inputs": {
                "host": {"connection": {"name": "@parameters('sftp_connection')"}},
                "method": "post",
                "path": "/datasets/default/files",
            },
        }
        return action, gaps

    # Unsupported connector — emit gap, return placeholder Compose
    gaps.append(
        _make_gap(
            construct_name=f"connector:{step.connector_type}",
            source_location=src,
            message=(
                f"Connector type '{step.connector_type}' has no built-in Logic Apps equivalent. "
                "Manual implementation required."
            ),
            category=GapCategory.CONNECTOR_MISMATCH,
            severity=Severity.ERROR,
            suggested_workaround=(
                f"Implement '{step.connector_type}' using an appropriate Logic Apps managed connector."
            ),
        )
    )
    action = {
        "type": "Compose",
        "inputs": {"MIGRATION_GAP": f"Connector '{step.connector_type}' not supported"},
    }
    return action, gaps


def _map_step(
    step: FlowStep,
    step_index: int,
    previous_action_name: str | None,
) -> tuple[str, dict[str, Any], list[MigrationGap]]:
    """Convert a single FlowStep to a named Logic Apps action dict.

    Returns:
        A tuple of (action_name, action_dict, gaps).
    """
    gaps: list[MigrationGap] = []
    src = _source_location_str(step)

    run_after: dict[str, list[str]] = {previous_action_name: ["Succeeded"]} if previous_action_name else {}

    # ── Processor ────────────────────────────────────────────────────────────
    if isinstance(step, Processor):
        raw_name = step.name or f"{step.type}_{step_index}"
        action_name = _sanitize_name(raw_name)

        if step.type == ProcessorType.LOGGER:
            action: dict[str, Any] = {
                "type": "Compose",
                "inputs": {
                    "level": step.config.get("level", "INFO"),
                    "message": step.config.get("message", ""),
                },
                "runAfter": run_after,
            }
        elif step.type == ProcessorType.SET_PAYLOAD:
            action = {
                "type": "Compose",
                "inputs": {"payload": step.config.get("value", "")},
                "runAfter": run_after,
            }
        elif step.type == ProcessorType.FLOW_REF:
            gaps.append(
                _make_gap(
                    construct_name="flow_ref",
                    source_location=src,
                    message="flow-ref resolution will be implemented in PR-010.",
                    category=GapCategory.UNRESOLVABLE_REFERENCE,
                    severity=Severity.WARNING,
                    suggested_workaround=("Manually link the referenced sub-flow after full project conversion."),
                )
            )
            ref_name = step.config.get("flow_name", "unknown")
            action = {
                "type": "Scope",
                "actions": {},
                "description": f"MIGRATION GAP: flow-ref to '{ref_name}' — resolve in PR-010",
                "runAfter": run_after,
            }
        else:
            gaps.append(
                _make_gap(
                    construct_name=f"processor:{step.type}",
                    source_location=src,
                    message=f"Processor type '{step.type}' has no direct Logic Apps equivalent.",
                    category=GapCategory.UNSUPPORTED_CONSTRUCT,
                    severity=Severity.WARNING,
                    suggested_workaround=("Implement the equivalent logic using available Logic Apps actions."),
                )
            )
            action = {
                "type": "Compose",
                "inputs": {},
                "description": f"MIGRATION GAP: processor '{step.type}' not supported",
                "runAfter": run_after,
            }

        return action_name, action, gaps

    # ── VariableOperation ─────────────────────────────────────────────────────
    if isinstance(step, VariableOperation):
        action_name = _sanitize_name(f"{step.operation}_variable_{step.variable_name}_{step_index}")

        if step.operation == "set":
            action = {
                "type": "InitializeVariable",
                "inputs": {
                    "variables": [
                        {
                            "name": step.variable_name,
                            "type": "String",
                            "value": step.value or "",
                        }
                    ]
                },
                "runAfter": run_after,
            }
        else:
            gaps.append(
                _make_gap(
                    construct_name=f"remove_variable:{step.variable_name}",
                    source_location=src,
                    message=(f"Remove-variable for '{step.variable_name}' has no direct Logic Apps equivalent."),
                    category=GapCategory.UNSUPPORTED_CONSTRUCT,
                    severity=Severity.WARNING,
                    suggested_workaround=(
                        "Variables in Logic Apps cannot be removed; set to null or empty string instead."
                    ),
                )
            )
            action = {
                "type": "Compose",
                "inputs": {"MIGRATION_GAP": f"remove_variable '{step.variable_name}' not supported"},
                "runAfter": run_after,
            }

        return action_name, action, gaps

    # ── Transform ─────────────────────────────────────────────────────────────
    if isinstance(step, Transform):
        action_name = _sanitize_name(f"transform_{step_index}")
        action = {
            "type": "Compose",
            "inputs": {"expression": step.expression or ""},
            "runAfter": run_after,
        }
        return action_name, action, gaps

    # ── ConnectorOperation ────────────────────────────────────────────────────
    if isinstance(step, ConnectorOperation):
        op_label = step.operation or "operation"
        action_name = _sanitize_name(f"{step.connector_type}_{op_label}_{step_index}")
        connector_action, connector_gaps = _map_connector_operation(step)
        connector_action["runAfter"] = run_after
        gaps.extend(connector_gaps)
        return action_name, connector_action, gaps

    # ── Router ────────────────────────────────────────────────────────────────
    if isinstance(step, Router):
        action_name = _sanitize_name(f"{step.type}_{step_index}")

        if step.type == RouterType.CHOICE:
            gaps.append(
                _make_gap(
                    construct_name="router:choice",
                    source_location=src,
                    message=(
                        "Choice router conditions require manual review — "
                        "DataWeave expressions are not automatically translated."
                    ),
                    category=GapCategory.PARTIAL_SUPPORT,
                    severity=Severity.WARNING,
                    suggested_workaround=(
                        "Review the generated If action and translate DataWeave conditions to Logic Apps expressions."
                    ),
                )
            )
            condition = ""
            if step.routes and step.routes[0].condition:
                condition = step.routes[0].condition
            action = {
                "type": "If",
                "expression": condition,
                "actions": {},
                "else": {"actions": {}},
                "runAfter": run_after,
            }

        elif step.type == RouterType.SCATTER_GATHER:
            gaps.append(
                _make_gap(
                    construct_name="router:scatter_gather",
                    source_location=src,
                    message=(
                        "Scatter-gather router has no direct Logic Apps equivalent. Manual parallel branching required."
                    ),
                    category=GapCategory.UNSUPPORTED_CONSTRUCT,
                    severity=Severity.ERROR,
                    suggested_workaround=(
                        "Implement parallel branches using Logic Apps Scope or parallel branch patterns."
                    ),
                )
            )
            action = {
                "type": "Scope",
                "actions": {},
                "description": "MIGRATION GAP: scatter-gather not supported",
                "runAfter": run_after,
            }

        else:
            gaps.append(
                _make_gap(
                    construct_name=f"router:{step.type}",
                    source_location=src,
                    message=f"Router type '{step.type}' has no direct Logic Apps equivalent.",
                    category=GapCategory.UNSUPPORTED_CONSTRUCT,
                    severity=Severity.ERROR,
                    suggested_workaround=(
                        "Implement the equivalent routing logic using Logic Apps conditional actions."
                    ),
                )
            )
            action = {
                "type": "Scope",
                "actions": {},
                "description": f"MIGRATION GAP: router '{step.type}' not supported",
                "runAfter": run_after,
            }

        return action_name, action, gaps

    # ── Scope ─────────────────────────────────────────────────────────────────
    if isinstance(step, Scope):
        action_name = _sanitize_name(f"{step.type}_{step_index}")

        if step.type == ScopeType.FOREACH:
            action = {
                "type": "Foreach",
                "foreach": step.config.get("collection", "@body()"),
                "actions": {},
                "runAfter": run_after,
            }
        elif step.type == ScopeType.TRY_SCOPE:
            action = {
                "type": "Scope",
                "actions": {},
                "runAfter": run_after,
            }
        else:
            gaps.append(
                _make_gap(
                    construct_name=f"scope:{step.type}",
                    source_location=src,
                    message=f"Scope type '{step.type}' has no direct Logic Apps equivalent.",
                    category=GapCategory.UNSUPPORTED_CONSTRUCT,
                    severity=Severity.WARNING,
                    suggested_workaround=("Implement the equivalent scoping logic using Logic Apps Scope actions."),
                )
            )
            action = {
                "type": "Scope",
                "actions": {},
                "description": f"MIGRATION GAP: scope '{step.type}' not supported",
                "runAfter": run_after,
            }

        return action_name, action, gaps

    # Unknown step type (defensive fallback)
    action_name = f"unknown_step_{step_index}"
    gaps.append(
        _make_gap(
            construct_name=f"unknown_step_{step_index}",
            source_location=src,
            message=f"Unknown step type at index {step_index}.",
            category=GapCategory.UNSUPPORTED_CONSTRUCT,
            severity=Severity.ERROR,
        )
    )
    action = {
        "type": "Compose",
        "inputs": {},
        "runAfter": run_after,
    }
    return action_name, action, gaps


def generate_workflow(flow: Flow) -> tuple[dict[str, Any], list[MigrationGap]]:
    """Convert a single IR Flow to a workflow.json dict.

    Builds the complete Logic Apps workflow definition including triggers,
    actions with runAfter chaining, and migration gap collection.

    Args:
        flow: The IR flow to convert.

    Returns:
        A tuple of (workflow_json_dict, migration_gaps).
    """
    all_gaps: list[MigrationGap] = []

    # Build triggers
    triggers_dict, _trigger_key, trigger_gaps = _map_trigger(flow)
    all_gaps.extend(trigger_gaps)

    # Build actions with runAfter chaining
    actions: dict[str, Any] = {}
    previous_action_name: str | None = None

    for step_index, step in enumerate(flow.steps):
        action_name, action_dict, step_gaps = _map_step(step, step_index, previous_action_name)
        all_gaps.extend(step_gaps)

        # Resolve name conflicts by appending the index
        if action_name in actions:
            action_name = f"{action_name}_{step_index}"

        actions[action_name] = action_dict
        previous_action_name = action_name

    workflow: dict[str, Any] = {
        "definition": {
            "$schema": WORKFLOW_SCHEMA,
            "contentVersion": "1.0.0.0",
            "triggers": triggers_dict,
            "actions": actions,
            "outputs": {},
        },
        "kind": "Stateful",
    }

    return workflow, all_gaps
