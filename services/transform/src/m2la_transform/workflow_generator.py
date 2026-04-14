"""Converts a single IR Flow into a Logic Apps Standard workflow.json dict.

Supports the full MVP construct set (spec §7):
- HTTP Listener → Request trigger
- Scheduler → Recurrence trigger
- Flow-ref / subflow → Scope with inlined steps
- Set-payload → Compose
- Set-variable → InitializeVariable
- Choice router → If (single condition) or Switch (multiple routes)
- Foreach → Foreach with nested actions
- Scatter-gather → Parallel branches pattern
- DataWeave → Compose with expression hints
- HTTP outbound → Http action
- File/FTP/SFTP → ApiConnection (SFTP built-in)
- SQL/Database → ApiConnection (SQL built-in)
- Messaging (JMS/VM) → ServiceBus ApiConnection
- Error handlers → Scope + runAfter failure conditions
- Unsupported constructs → explicit MigrationGap (never silently dropped)
"""

from __future__ import annotations

import re
from typing import Any

from m2la_contracts.common import MigrationGap
from m2la_contracts.enums import GapCategory, Severity
from m2la_ir.enums import (
    ConnectorType,
    ErrorHandlerType,
    ProcessorType,
    RouterType,
    ScopeType,
    TransformType,
    TriggerType,
)
from m2la_ir.models import (
    ConnectorOperation,
    ErrorHandler,
    Flow,
    FlowStep,
    Processor,
    Router,
    Scope,
    Transform,
    VariableOperation,
)

WORKFLOW_SCHEMA = (
    "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
)

# ── Named constants for generated Logic Apps expressions ──────────────────────

# Placeholder expression for Until loops converted from until-successful.
# Always evaluates to true so the loop relies solely on the count limit.
# Must be reviewed and replaced with a real exit condition post-migration.
UNTIL_LOOP_PLACEHOLDER_EXPR = "@equals(1, 1)"

# Placeholder variable name for Switch actions converted from multi-branch
# choice routers. The migrator cannot infer the correct switch expression —
# users must set this to an appropriate Logic Apps expression post-migration.
SWITCH_PLACEHOLDER_EXPR = "@variables('switchExpression')"

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

# ── DataWeave → Logic Apps expression helpers ─────────────────────────────────

# Simple DataWeave patterns we can auto-translate to Logic Apps expressions.
_DW_SIMPLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^payload$"), "@triggerBody()"),
    (re.compile(r"^payload\.(\w+)$"), r"@triggerBody()?['\1']"),
    (re.compile(r"^vars\.(\w+)$"), r"@variables('\1')"),
    (re.compile(r"^attributes\.(\w+)$"), r"@triggerOutputs()?['headers']['\1']"),
]


def convert_dataweave_expression(dw_expr: str) -> tuple[str, bool]:
    """Attempt to convert a DataWeave expression to a Logic Apps expression.

    Returns:
        A tuple of (converted_expression, was_converted).  When *was_converted*
        is False the caller should emit a migration gap advising manual review.
    """
    stripped = dw_expr.strip()

    # Strip surrounding #[…] wrapper used in Mule expression syntax
    if stripped.startswith("#[") and stripped.endswith("]"):
        stripped = stripped[2:-1].strip()

    for pattern, replacement in _DW_SIMPLE_PATTERNS:
        match = pattern.match(stripped)
        if match:
            return match.expand(replacement), True

    # If the expression is a multi-line DataWeave script, we cannot translate
    return dw_expr, False


# ── Name helpers ──────────────────────────────────────────────────────────────


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


# ── Recursive step conversion ────────────────────────────────────────────────


def _convert_steps(
    steps: list[FlowStep],
    sub_flows: dict[str, Flow] | None = None,
) -> tuple[dict[str, Any], list[MigrationGap]]:
    """Recursively convert a list of FlowSteps into a flat {name: action} dict.

    Actions are chained via runAfter to preserve execution order.

    Args:
        steps: Ordered list of flow steps.
        sub_flows: Mapping of sub-flow name → Flow for flow-ref resolution.

    Returns:
        A tuple of (actions_dict, migration_gaps).
    """
    sub_flows = sub_flows or {}
    all_gaps: list[MigrationGap] = []
    actions: dict[str, Any] = {}
    previous_action_name: str | None = None

    for step_index, step in enumerate(steps):
        action_name, action_dict, step_gaps = _map_step(
            step,
            step_index,
            previous_action_name,
            sub_flows=sub_flows,
        )
        all_gaps.extend(step_gaps)

        # Resolve name conflicts
        if action_name in actions:
            action_name = f"{action_name}_{step_index}"

        actions[action_name] = action_dict
        previous_action_name = action_name

    return actions, all_gaps


# ── Trigger mapping ──────────────────────────────────────────────────────────


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


# ── Connector operation mapping ───────────────────────────────────────────────


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
        # Include headers if present
        if config.get("headers"):
            action["inputs"]["headers"] = config["headers"]
        return action, gaps

    if step.connector_type == ConnectorType.DB:
        operation = step.operation or "select"
        query = config.get("query", "")
        action = {
            "type": "ApiConnection",
            "inputs": {
                "host": {"connection": {"name": "@parameters('sql_connection')"}},
                "method": "post",
                "path": "/datasets/default/query/sql",
                "body": {"query": query},
            },
        }
        if operation != "select":
            action["inputs"]["path"] = "/datasets/default/procedures/execute"
        return action, gaps

    if step.connector_type == ConnectorType.MQ:
        destination = config.get("destination", "default-topic")
        action = {
            "type": "ApiConnection",
            "inputs": {
                "host": {"connection": {"name": "@parameters('servicebus_connection')"}},
                "method": "post",
                "path": f"/{destination}/messages",
                "body": config.get("body", {}),
            },
        }
        return action, gaps

    if step.connector_type in (ConnectorType.FTP, ConnectorType.SFTP):
        file_path = config.get("path", "/")
        operation = step.operation or "write"
        action = {
            "type": "ApiConnection",
            "inputs": {
                "host": {"connection": {"name": "@parameters('sftp_connection')"}},
                "method": "post",
                "path": f"/datasets/default/files/{file_path}",
            },
        }
        if operation == "read":
            action["inputs"]["method"] = "get"
            action["inputs"]["path"] = f"/datasets/default/files/{file_path}/content"
        return action, gaps

    if step.connector_type == ConnectorType.FILE:
        file_path = config.get("path", "/")
        action = {
            "type": "ApiConnection",
            "inputs": {
                "host": {"connection": {"name": "@parameters('filesystem_connection')"}},
                "method": "post",
                "path": f"/datasets/default/files/{file_path}",
            },
        }
        return action, gaps

    if step.connector_type == ConnectorType.VM:
        queue_name = config.get("queueName", "default-queue")
        action = {
            "type": "ApiConnection",
            "inputs": {
                "host": {"connection": {"name": "@parameters('servicebus_connection')"}},
                "method": "post",
                "path": f"/{queue_name}/messages",
                "body": config.get("body", {}),
            },
        }
        gaps.append(
            _make_gap(
                construct_name=f"connector:{step.connector_type}",
                source_location=src,
                message=(
                    "Mule VM (in-memory) queues mapped to Service Bus. "
                    "Async/transient semantics are not fully preserved."
                ),
                category=GapCategory.PARTIAL_SUPPORT,
                severity=Severity.WARNING,
                suggested_workaround="Review Service Bus queue settings for transient semantics.",
            )
        )
        return action, gaps

    if step.connector_type == ConnectorType.EMAIL:
        action = {
            "type": "ApiConnection",
            "inputs": {
                "host": {"connection": {"name": "@parameters('office365_connection')"}},
                "method": "post",
                "path": "/v2/Mail",
                "body": {
                    "To": config.get("to", ""),
                    "Subject": config.get("subject", ""),
                    "Body": config.get("body", ""),
                },
            },
        }
        gaps.append(
            _make_gap(
                construct_name=f"connector:{step.connector_type}",
                source_location=src,
                message=(
                    "Email/SMTP mapped to Office 365 Outlook managed connector. SMTP auth must be migrated to OAuth2."
                ),
                category=GapCategory.PARTIAL_SUPPORT,
                severity=Severity.WARNING,
                suggested_workaround="Configure OAuth2 for the Office 365 Outlook connector.",
            )
        )
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


# ── Error handler mapping ────────────────────────────────────────────────────


def _map_error_handlers(
    error_handlers: list[ErrorHandler],
    preceding_action_name: str,
    sub_flows: dict[str, Flow] | None = None,
) -> tuple[dict[str, Any], list[MigrationGap]]:
    """Convert error handlers into Scope actions with runAfter failure conditions.

    Each error handler becomes a Scope that runs after the preceding action
    fails, is skipped, or times out — matching Mule on-error-propagate /
    on-error-continue semantics as closely as Logic Apps allows.

    Returns:
        (actions_dict, gaps) — the error-handling actions to merge into the
        workflow's top-level actions.
    """
    actions: dict[str, Any] = {}
    gaps: list[MigrationGap] = []

    for idx, handler in enumerate(error_handlers):
        handler_name = _sanitize_name(f"error_handler_{handler.type}_{idx}")

        # Build nested actions from the handler's steps
        inner_actions, inner_gaps = _convert_steps(handler.steps, sub_flows)
        gaps.extend(inner_gaps)

        # Both handler types run on failure — Logic Apps doesn't distinguish
        # between propagate/continue at the runAfter level; the difference is
        # modeled via scope nesting and description annotations.
        run_after_statuses = ["Failed", "TimedOut"]

        scope_action: dict[str, Any] = {
            "type": "Scope",
            "actions": inner_actions,
            "runAfter": {preceding_action_name: run_after_statuses},
        }

        # Annotate error type filter if specified
        if handler.error_type:
            scope_action["description"] = f"Error handler for type '{handler.error_type}' ({handler.type})"

        if handler.type == ErrorHandlerType.ON_ERROR_CONTINUE:
            scope_action["description"] = scope_action.get("description", "") + (
                " — continues execution (errors are suppressed)"
            )

        actions[handler_name] = scope_action

    return actions, gaps


# ── Step mapping ──────────────────────────────────────────────────────────────


def _map_step(
    step: FlowStep,
    step_index: int,
    previous_action_name: str | None,
    *,
    sub_flows: dict[str, Flow] | None = None,
) -> tuple[str, dict[str, Any], list[MigrationGap]]:
    """Convert a single FlowStep to a named Logic Apps action dict.

    Recursively converts nested steps in scopes and routers.

    Args:
        step: The IR flow step to convert.
        step_index: Positional index within the parent step list.
        previous_action_name: The preceding action name for runAfter chaining.
        sub_flows: Sub-flow lookup for flow-ref resolution.

    Returns:
        A tuple of (action_name, action_dict, gaps).
    """
    sub_flows = sub_flows or {}
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
            value = step.config.get("value", "")
            converted, _ = convert_dataweave_expression(value)
            action = {
                "type": "Compose",
                "inputs": {"payload": converted},
                "runAfter": run_after,
            }
        elif step.type == ProcessorType.FLOW_REF:
            ref_name = step.config.get("flow_name", "unknown")
            referenced_flow = sub_flows.get(ref_name)

            if referenced_flow is not None:
                # Inline sub-flow steps as a Scope
                inner_actions, inner_gaps = _convert_steps(
                    referenced_flow.steps,
                    sub_flows,
                )
                gaps.extend(inner_gaps)
                action = {
                    "type": "Scope",
                    "actions": inner_actions,
                    "runAfter": run_after,
                    "description": f"Inlined sub-flow '{ref_name}'",
                }
            else:
                # Sub-flow not found — emit warning but never silently drop
                gaps.append(
                    _make_gap(
                        construct_name="flow_ref",
                        source_location=src,
                        message=(
                            f"flow-ref to '{ref_name}' could not be resolved. "
                            "The referenced sub-flow was not found in the current project."
                        ),
                        category=GapCategory.UNRESOLVABLE_REFERENCE,
                        severity=Severity.WARNING,
                        suggested_workaround=(
                            "Manually link the referenced sub-flow or convert it to a "
                            "separate workflow and use HTTP/Service Bus bridging."
                        ),
                    )
                )
                action = {
                    "type": "Scope",
                    "actions": {},
                    "description": f"MIGRATION GAP: flow-ref to '{ref_name}' could not be resolved",
                    "runAfter": run_after,
                }
        elif step.type == ProcessorType.RAISE_ERROR:
            error_type = step.config.get("type", "CUSTOM:ERROR")
            error_desc = step.config.get("description", "")
            action = {
                "type": "Terminate",
                "inputs": {
                    "runStatus": "Failed",
                    "runError": {
                        "code": error_type,
                        "message": error_desc,
                    },
                },
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
            value = step.value or ""
            converted, _ = convert_dataweave_expression(value)
            action = {
                "type": "InitializeVariable",
                "inputs": {
                    "variables": [
                        {
                            "name": step.variable_name,
                            "type": "String",
                            "value": converted,
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
        expression = step.expression or ""
        converted, was_converted = convert_dataweave_expression(expression)

        action = {
            "type": "Compose",
            "inputs": {"expression": converted},
            "runAfter": run_after,
        }

        if step.type == TransformType.DATAWEAVE and not was_converted:
            gaps.append(
                _make_gap(
                    construct_name="dataweave_transform",
                    source_location=src,
                    message=(
                        "Complex DataWeave expression could not be auto-translated. "
                        "Manual conversion to Logic Apps expressions or inline code required."
                    ),
                    category=GapCategory.DATAWEAVE_COMPLEXITY,
                    severity=Severity.WARNING,
                    suggested_workaround=(
                        "Review the DataWeave expression and convert to Logic Apps workflow "
                        "expression language or use an Azure Function for complex transformations."
                    ),
                )
            )

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
            return _map_choice_router(step, action_name, run_after, src, sub_flows)

        if step.type == RouterType.SCATTER_GATHER:
            return _map_scatter_gather(step, action_name, run_after, src, sub_flows)

        # Unsupported router types
        gaps.append(
            _make_gap(
                construct_name=f"router:{step.type}",
                source_location=src,
                message=f"Router type '{step.type}' has no direct Logic Apps equivalent.",
                category=GapCategory.UNSUPPORTED_CONSTRUCT,
                severity=Severity.ERROR,
                suggested_workaround=("Implement the equivalent routing logic using Logic Apps conditional actions."),
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
            inner_actions, inner_gaps = _convert_steps(step.steps, sub_flows)
            gaps.extend(inner_gaps)
            collection_expr = step.config.get("collection", "@body()")
            converted_coll, _ = convert_dataweave_expression(collection_expr)
            action = {
                "type": "Foreach",
                "foreach": converted_coll,
                "actions": inner_actions,
                "runAfter": run_after,
            }
            return action_name, action, gaps

        if step.type == ScopeType.PARALLEL_FOREACH:
            inner_actions, inner_gaps = _convert_steps(step.steps, sub_flows)
            gaps.extend(inner_gaps)
            collection_expr = step.config.get("collection", "@body()")
            converted_coll, _ = convert_dataweave_expression(collection_expr)
            action = {
                "type": "Foreach",
                "foreach": converted_coll,
                "actions": inner_actions,
                "runAfter": run_after,
                "runtimeConfiguration": {
                    "concurrency": {"repetitions": step.config.get("max_concurrency", 20)},
                },
            }
            return action_name, action, gaps

        if step.type == ScopeType.TRY_SCOPE:
            inner_actions, inner_gaps = _convert_steps(step.steps, sub_flows)
            gaps.extend(inner_gaps)
            action = {
                "type": "Scope",
                "actions": inner_actions,
                "runAfter": run_after,
            }
            return action_name, action, gaps

        if step.type == ScopeType.UNTIL_SUCCESSFUL:
            inner_actions, inner_gaps = _convert_steps(step.steps, sub_flows)
            gaps.extend(inner_gaps)
            max_retries = step.config.get("maxRetries", 5)
            action = {
                "type": "Until",
                "actions": inner_actions,
                "expression": UNTIL_LOOP_PLACEHOLDER_EXPR,
                "limit": {
                    "count": max_retries,
                    "timeout": "PT1H",
                },
                "runAfter": run_after,
            }
            gaps.append(
                _make_gap(
                    construct_name="scope:until_successful",
                    source_location=src,
                    message=("until-successful mapped to Until loop. Review loop condition and retry parameters."),
                    category=GapCategory.PARTIAL_SUPPORT,
                    severity=Severity.WARNING,
                    suggested_workaround="Adjust the Until loop expression and limit to match retry semantics.",
                )
            )
            return action_name, action, gaps

        if step.type == ScopeType.ASYNC_SCOPE:
            inner_actions, inner_gaps = _convert_steps(step.steps, sub_flows)
            gaps.extend(inner_gaps)
            action = {
                "type": "Scope",
                "actions": inner_actions,
                "runAfter": run_after,
                "description": (
                    "Converted from async scope — fire-and-forget semantics are not preserved. Review carefully."
                ),
            }
            gaps.append(
                _make_gap(
                    construct_name="scope:async_scope",
                    source_location=src,
                    message=("Async scope converted to sequential Scope. Fire-and-forget semantics are not preserved."),
                    category=GapCategory.PARTIAL_SUPPORT,
                    severity=Severity.WARNING,
                    suggested_workaround=(
                        "Consider using a separate workflow triggered via HTTP or Service Bus for true async behavior."
                    ),
                )
            )
            return action_name, action, gaps

        # Unknown scope type
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
        inner_actions, inner_gaps = _convert_steps(step.steps, sub_flows)
        gaps.extend(inner_gaps)
        action = {
            "type": "Scope",
            "actions": inner_actions,
            "description": f"MIGRATION GAP: scope '{step.type}' not supported",
            "runAfter": run_after,
        }
        return action_name, action, gaps

    # Unknown step type (defensive fallback — never silently drop)
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


# ── Choice router mapping ────────────────────────────────────────────────────


def _map_choice_router(
    step: Router,
    action_name: str,
    run_after: dict[str, list[str]],
    src: str,
    sub_flows: dict[str, Flow],
) -> tuple[str, dict[str, Any], list[MigrationGap]]:
    """Map a choice router to Logic Apps If or Switch action with nested actions."""
    gaps: list[MigrationGap] = []

    if len(step.routes) <= 1:
        # Single-condition → If action
        condition_expr = ""
        true_actions: dict[str, Any] = {}
        else_actions: dict[str, Any] = {}

        if step.routes:
            first_route = step.routes[0]
            raw_condition = first_route.condition or ""
            condition_expr, was_converted = convert_dataweave_expression(raw_condition)
            if not was_converted and raw_condition:
                gaps.append(
                    _make_gap(
                        construct_name="router:choice",
                        source_location=src,
                        message=(
                            "Choice router condition could not be auto-translated. "
                            "Manual review of the expression is required."
                        ),
                        category=GapCategory.PARTIAL_SUPPORT,
                        severity=Severity.WARNING,
                        suggested_workaround=("Convert the DataWeave condition to a Logic Apps expression."),
                    )
                )
            true_actions, inner_gaps = _convert_steps(first_route.steps, sub_flows)
            gaps.extend(inner_gaps)

        if step.default_route:
            else_actions, inner_gaps = _convert_steps(step.default_route.steps, sub_flows)
            gaps.extend(inner_gaps)

        action: dict[str, Any] = {
            "type": "If",
            "expression": condition_expr,
            "actions": true_actions,
            "else": {"actions": else_actions},
            "runAfter": run_after,
        }
        return action_name, action, gaps

    # Multiple conditions → Switch action
    cases: dict[str, Any] = {}
    for route_idx, route in enumerate(step.routes):
        case_actions, inner_gaps = _convert_steps(route.steps, sub_flows)
        gaps.extend(inner_gaps)

        raw_condition = route.condition or f"case_{route_idx}"
        converted_cond, was_converted = convert_dataweave_expression(raw_condition)
        if not was_converted and route.condition:
            gaps.append(
                _make_gap(
                    construct_name="router:choice",
                    source_location=src,
                    message=(f"Choice router condition for case {route_idx} could not be auto-translated."),
                    category=GapCategory.PARTIAL_SUPPORT,
                    severity=Severity.WARNING,
                    suggested_workaround="Convert the DataWeave condition to a Logic Apps expression.",
                )
            )

        case_name = f"Case_{route_idx}"
        cases[case_name] = {
            "case": converted_cond,
            "actions": case_actions,
        }

    default_actions: dict[str, Any] = {}
    if step.default_route:
        default_actions, inner_gaps = _convert_steps(step.default_route.steps, sub_flows)
        gaps.extend(inner_gaps)

    action = {
        "type": "Switch",
        "expression": SWITCH_PLACEHOLDER_EXPR,
        "cases": cases,
        "default": {"actions": default_actions},
        "runAfter": run_after,
    }
    gaps.append(
        _make_gap(
            construct_name="router:choice",
            source_location=src,
            message=("Multi-branch choice router mapped to Switch action. The switch expression must be set manually."),
            category=GapCategory.PARTIAL_SUPPORT,
            severity=Severity.WARNING,
            suggested_workaround=(
                "Set the Switch 'expression' to the appropriate Logic Apps expression "
                "that evaluates to one of the case values."
            ),
        )
    )
    return action_name, action, gaps


# ── Scatter-gather mapping ────────────────────────────────────────────────────


def _map_scatter_gather(
    step: Router,
    action_name: str,
    run_after: dict[str, list[str]],
    src: str,
    sub_flows: dict[str, Flow],
) -> tuple[str, dict[str, Any], list[MigrationGap]]:
    """Map a scatter-gather router to Logic Apps parallel branch pattern.

    Logic Apps parallel branches work by giving multiple actions the same
    runAfter predecessor.  We wrap each scatter-gather route in its own Scope
    and then add a join Scope that depends on all branch scopes succeeding.
    """
    gaps: list[MigrationGap] = []
    all_actions: dict[str, Any] = {}
    branch_names: list[str] = []

    for route_idx, route in enumerate(step.routes):
        branch_actions, inner_gaps = _convert_steps(route.steps, sub_flows)
        gaps.extend(inner_gaps)

        branch_name = f"Branch_{route_idx}"
        branch_scope: dict[str, Any] = {
            "type": "Scope",
            "actions": branch_actions,
            "runAfter": run_after,
        }
        all_actions[branch_name] = branch_scope
        branch_names.append(branch_name)

    # Join scope that waits for all branches
    if branch_names:
        join_run_after = {name: ["Succeeded"] for name in branch_names}
        all_actions["Join_Branches"] = {
            "type": "Compose",
            "inputs": {"status": "all branches completed"},
            "runAfter": join_run_after,
        }

    gaps.append(
        _make_gap(
            construct_name="router:scatter_gather",
            source_location=src,
            message=("Scatter-gather mapped to parallel branch pattern. Aggregation logic must be manually reviewed."),
            category=GapCategory.PARTIAL_SUPPORT,
            severity=Severity.WARNING,
            suggested_workaround=(
                "Review the Join_Branches action and implement any aggregation "
                "logic that was present in the original scatter-gather."
            ),
        )
    )

    # Wrap everything in a parent Scope for clean nesting
    action: dict[str, Any] = {
        "type": "Scope",
        "actions": all_actions,
        "runAfter": run_after,
    }
    return action_name, action, gaps


# ── Public API ────────────────────────────────────────────────────────────────


def generate_workflow(
    flow: Flow,
    sub_flows: dict[str, Flow] | None = None,
) -> tuple[dict[str, Any], list[MigrationGap]]:
    """Convert a single IR Flow to a workflow.json dict.

    Builds the complete Logic Apps workflow definition including triggers,
    actions with runAfter chaining, error handler scopes, and migration gap
    collection.

    Args:
        flow: The IR flow to convert.
        sub_flows: Optional mapping of sub-flow name → Flow for flow-ref
            resolution.  When generating a full project, pass all sub-flows
            so that flow-ref steps can be inlined.

    Returns:
        A tuple of (workflow_json_dict, migration_gaps).
    """
    sub_flows = sub_flows or {}
    all_gaps: list[MigrationGap] = []

    # Build triggers
    triggers_dict, _trigger_key, trigger_gaps = _map_trigger(flow)
    all_gaps.extend(trigger_gaps)

    # Build actions with runAfter chaining (recursive)
    actions, step_gaps = _convert_steps(flow.steps, sub_flows)
    all_gaps.extend(step_gaps)

    # Build error handler scopes
    if flow.error_handlers:
        # Find the last action name from the main step chain
        last_action_name = list(actions.keys())[-1] if actions else ""
        if last_action_name:
            error_actions, error_gaps = _map_error_handlers(
                flow.error_handlers,
                last_action_name,
                sub_flows,
            )
            all_gaps.extend(error_gaps)
            actions.update(error_actions)

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
