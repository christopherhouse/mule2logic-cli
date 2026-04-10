"""JSON validation — ensures agent output is valid Logic Apps JSON."""

from __future__ import annotations

import json
import re
from typing import Any

from mule2logic_agent.models import WorkflowDefinition


def validate_json(output: str) -> WorkflowDefinition:
    """Parse and validate agent output as Logic Apps workflow JSON.

    Applies multiple strategies to extract valid JSON:
      1. Strip markdown code fences.
      2. Extract the first ``{ … }`` block if leading text is present.

    Raises ``ValueError`` on any structural validation failure.
    """
    if not isinstance(output, str) or not output.strip():
        raise ValueError("Output is empty or not a string")

    cleaned = output.strip()

    # Strategy 1: strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Strategy 2: extract the first { … } block
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]

    try:
        parsed: dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("Output is not valid JSON") from exc

    if not isinstance(parsed.get("definition"), dict):
        raise ValueError('Missing required "definition" property')

    if not isinstance(parsed["definition"].get("actions"), dict):
        raise ValueError('Missing required "definition.actions" property')

    return parsed


def validate_workflow_structure(parsed: WorkflowDefinition) -> list[str]:
    """Deep structural validation of a Logic Apps workflow definition.

    Returns a list of warning/error strings.  Empty list means valid.
    """
    issues: list[str] = []
    definition = parsed["definition"]

    # Check triggers
    triggers = definition.get("triggers")
    if isinstance(triggers, dict):
        for name, trigger in triggers.items():
            if not isinstance(trigger, dict) or not isinstance(
                trigger.get("type"), str
            ):
                issues.append(f'Trigger "{name}" is missing a "type" field')

    # Check actions
    actions: dict[str, Any] = definition["actions"]
    action_names = set(actions.keys())

    for name, action in actions.items():
        if not isinstance(action, dict):
            continue

        if not isinstance(action.get("type"), str):
            issues.append(f'Action "{name}" is missing a "type" field')

        # Validate runAfter references
        run_after = action.get("runAfter")
        if isinstance(run_after, dict):
            for dep in run_after:
                if dep not in action_names:
                    issues.append(
                        f'Action "{name}" has runAfter reference to '
                        f'non-existent action "{dep}"'
                    )

        # Condition (If) validation
        if action.get("type") == "If":
            if not action.get("expression"):
                issues.append(
                    f'Condition action "{name}" is missing "expression"'
                )
            if not action.get("actions") and not action.get("else"):
                issues.append(
                    f'Condition action "{name}" has no "actions" or "else" branches'
                )

        # Foreach validation
        if action.get("type") == "Foreach":
            if not action.get("foreach"):
                issues.append(
                    f'Foreach action "{name}" is missing "foreach" input'
                )
            if not isinstance(action.get("actions"), dict):
                issues.append(
                    f'Foreach action "{name}" is missing nested "actions"'
                )

    return issues
