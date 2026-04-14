"""Deterministic service functions exposed as Azure AI Agent FunctionTool callables.

Each function wraps a deterministic service call and returns a JSON-serializable
``str`` result.  These functions serve as the tools that SDK-created agents can
invoke when running in **online** mode (backed by the Azure AI Agent Service).

The functions intentionally keep their signatures simple — only primitive /
JSON-serialisable parameters — because the SDK uses introspection to generate
OpenAI-compatible function schemas exposed to the backing LLM.
"""

from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# AnalyzerAgent tool
# ---------------------------------------------------------------------------


def analyze_mule_input(input_path: str, mode: str | None = None) -> str:
    """Parse and analyse a MuleSoft project or flow XML file.

    Calls the deterministic parser, IR builder, and input validator to
    produce a structured analysis summary.

    Args:
        input_path: Filesystem path to a Mule project directory or a
            standalone flow XML file.
        mode: Optional input mode override (``"project"`` or
            ``"single_flow"``).  Auto-detected when *None*.

    Returns:
        JSON string with keys ``flow_count``, ``subflow_count``,
        ``construct_count``, ``warnings``, and ``mode``.
    """
    from m2la_contracts.enums import InputMode
    from m2la_contracts.helpers import detect_input_mode
    from m2la_parser.parse import parse
    from m2la_validate.engine import validate_mule_input

    resolved_mode: InputMode
    if mode is not None:
        resolved_mode = InputMode(mode)
    else:
        resolved_mode = detect_input_mode(input_path)

    inventory = parse(input_path, mode=resolved_mode)
    validation_report = validate_mule_input(Path(input_path), resolved_mode)

    warnings: list[str] = [f"{w.code}: {w.message}" for w in inventory.warnings]
    for issue in validation_report.issues:
        warnings.append(f"{issue.rule_id}: {issue.message}")

    return json.dumps(
        {
            "flow_count": len(inventory.flows),
            "subflow_count": len(inventory.subflows),
            "construct_count": sum(len(f.processors) for f in inventory.flows),
            "warnings": warnings,
            "mode": resolved_mode.value,
            "validation_valid": validation_report.valid,
        }
    )


# ---------------------------------------------------------------------------
# PlannerAgent tool
# ---------------------------------------------------------------------------


def create_migration_plan(ir_json: str) -> str:
    """Create a migration plan from an intermediate representation.

    Loads the mapping configuration and evaluates which MuleSoft
    constructs can be migrated to Logic Apps.

    Args:
        ir_json: JSON-serialised summary of the intermediate
            representation (must contain at least ``construct_names``
            and ``flow_count``).

    Returns:
        JSON string describing supported / unsupported / partial counts
        and per-construct mapping decisions.
    """
    from m2la_mapping_config.loader import load_all
    from m2la_mapping_config.resolver import MappingResolver

    ir_data: dict = json.loads(ir_json)
    construct_names: list[str] = ir_data.get("construct_names", [])
    flow_count: int = ir_data.get("flow_count", 0)

    try:
        mapping_config = load_all()
    except FileNotFoundError:
        mapping_config = None

    construct_summary: dict[str, int] = {}
    for name in construct_names:
        construct_summary[name] = construct_summary.get(name, 0) + 1

    supported = 0
    unsupported = 0
    partial = 0
    decisions: list[dict] = []

    if mapping_config is not None:
        resolver = MappingResolver(mapping_config)
        seen: set[str] = set()
        for element_name in construct_names:
            if element_name in seen:
                continue
            seen.add(element_name)
            construct_entry = resolver.resolve_construct(element_name)
            count = construct_summary.get(element_name, 0)
            if construct_entry is not None:
                if construct_entry.supported:
                    supported += count
                    decisions.append(
                        {
                            "mule_element": element_name,
                            "status": "supported",
                            "logic_apps_equivalent": construct_entry.logic_apps_type,
                            "notes": construct_entry.notes,
                        }
                    )
                else:
                    partial += count
                    decisions.append(
                        {
                            "mule_element": element_name,
                            "status": "partial",
                            "logic_apps_equivalent": construct_entry.logic_apps_type,
                            "notes": construct_entry.notes,
                        }
                    )
            else:
                unsupported += count
                decisions.append(
                    {
                        "mule_element": element_name,
                        "status": "unsupported",
                    }
                )
    else:
        for element_name, count in construct_summary.items():
            unsupported += count
            decisions.append(
                {
                    "mule_element": element_name,
                    "status": "unsupported",
                    "notes": "Mapping config unavailable",
                }
            )

    return json.dumps(
        {
            "flow_count": flow_count,
            "construct_summary": construct_summary,
            "supported_count": supported,
            "unsupported_count": unsupported,
            "partial_count": partial,
            "mapping_decisions": decisions,
            "estimated_gaps": unsupported + partial,
        }
    )


# ---------------------------------------------------------------------------
# TransformerAgent tool
# ---------------------------------------------------------------------------


def transform_to_logic_apps(
    ir_json: str,
    mode: str,
    output_directory: str | None = None,
) -> str:
    """Transform a MuleSoft IR into Logic Apps artifacts.

    Delegates to the deterministic transform service.

    Args:
        ir_json: JSON-serialised intermediate representation summary.
        mode: Input mode — ``"project"`` or ``"single_flow"``.
        output_directory: Filesystem path for generated artifacts
            (project mode only).

    Returns:
        JSON string with keys ``workflow_count``, ``gap_count``, and
        ``mode``.
    """
    # NOTE: In the online path the LLM orchestrates calls; the heavy
    # lifting is already done by the offline ``execute()`` method.
    # This stub returns a lightweight summary so the LLM can reason.
    data: dict = json.loads(ir_json)
    flow_count: int = data.get("flow_count", 0)

    return json.dumps(
        {
            "mode": mode,
            "flow_count": flow_count,
            "output_directory": output_directory,
            "status": "transform_ready",
        }
    )


# ---------------------------------------------------------------------------
# ValidatorAgent tool
# ---------------------------------------------------------------------------


def validate_output_artifacts(output_path: str, mode: str) -> str:
    """Validate generated Logic Apps artifacts.

    Runs the deterministic validation engine against the output.

    Args:
        output_path: Filesystem path to the generated output directory
            or a workflow dict path.
        mode: Input mode — ``"project"`` or ``"single_flow"``.

    Returns:
        JSON string with validation summary.
    """
    from m2la_contracts.enums import InputMode
    from m2la_validate.engine import validate_output

    resolved_mode = InputMode(mode)
    target = Path(output_path)
    report = validate_output(target, resolved_mode)

    issues = [{"rule_id": i.rule_id, "message": i.message, "severity": i.severity.value} for i in report.issues]

    return json.dumps(
        {
            "valid": report.valid,
            "artifacts_validated": report.artifacts_validated,
            "issue_count": len(report.issues),
            "issues": issues,
        }
    )


# ---------------------------------------------------------------------------
# RepairAdvisorAgent tool
# ---------------------------------------------------------------------------


def suggest_repairs(
    validation_report_json: str,
    migration_gaps_json: str,
) -> str:
    """Suggest repairs for validation issues and migration gaps.

    Maps known validation rule IDs and gap categories to predefined
    repair strategies.

    Args:
        validation_report_json: JSON array of validation issues, each
            with ``rule_id``, ``message``, and ``severity``.
        migration_gaps_json: JSON array of migration gaps, each with
            ``category`` and ``construct_name``.

    Returns:
        JSON array of repair suggestions.
    """
    issues: list[dict] = json.loads(validation_report_json)
    gaps: list[dict] = json.loads(migration_gaps_json)

    suggestions: list[dict] = []

    _rule_hints: dict[str, str] = {
        "MULE_": "Review the MuleSoft input for structural issues; ensure valid XML and proper namespaces.",
        "IR_": "Check IR construction — ensure all flows have valid triggers and steps.",
        "OUT_": "Verify generated workflow.json schema and action references.",
    }

    for issue in issues:
        rule_id = issue.get("rule_id", "")
        message = issue.get("message", "")
        hint = None
        for prefix, text in _rule_hints.items():
            if rule_id.startswith(prefix):
                hint = text
                break
        if hint is None:
            hint = f"Review issue: {message}"
        suggestions.append(
            {
                "issue_ref": rule_id,
                "suggestion": hint,
                "confidence": "medium",
                "auto_fixable": False,
            }
        )

    _gap_hints: dict[str, str] = {
        "unsupported_construct": "No Logic Apps equivalent. Consider an Azure Function.",
        "unresolvable_reference": "Ensure all config-refs and flow-refs are defined.",
        "partial_support": "Partially supported. Review output and add manual adjustments.",
        "connector_mismatch": "Verify authentication and connection settings.",
        "dataweave_complexity": "Complex DataWeave needs manual conversion — consider Liquid templates.",
    }

    for gap in gaps:
        category = gap.get("category", "")
        construct_name = gap.get("construct_name", "unknown")
        hint = _gap_hints.get(category, f"Migration gap for '{construct_name}': apply manual fix.")
        suggestions.append(
            {
                "issue_ref": construct_name,
                "suggestion": hint,
                "confidence": "medium",
                "auto_fixable": False,
            }
        )

    return json.dumps(suggestions)
