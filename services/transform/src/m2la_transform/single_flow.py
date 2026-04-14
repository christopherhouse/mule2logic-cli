"""Single-flow mode entry point and top-level generate() dispatcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from m2la_contracts.common import MigrationGap
from m2la_contracts.enums import InputMode
from m2la_ir.models import Flow, MuleIR

from m2la_transform.generator import generate_project
from m2la_transform.models import ProjectArtifacts
from m2la_transform.workflow_generator import WORKFLOW_SCHEMA, generate_workflow

_EMPTY_WORKFLOW: dict[str, Any] = {
    "definition": {
        "$schema": WORKFLOW_SCHEMA,
        "actions": {},
        "contentVersion": "1.0.0.0",
        "outputs": {},
        "triggers": {},
    },
    "kind": "Stateful",
}


def generate_single_flow_workflow(flow: Flow) -> tuple[dict[str, Any], list[MigrationGap]]:
    """Generate a workflow.json dict for a single flow without writing any files.

    This is the primary entry point for single-flow conversion mode.

    Args:
        flow: The IR flow to convert.

    Returns:
        A tuple of (workflow_json_dict, migration_gaps).
    """
    return generate_workflow(flow)


def generate(
    ir: MuleIR,
    output_dir: Path | None = None,
) -> tuple[ProjectArtifacts | dict[str, Any], list[MigrationGap]]:
    """Top-level generation entry point that dispatches on IR source mode.

    - ``InputMode.PROJECT``     → calls :func:`generate_project` and returns
      ``(ProjectArtifacts, gaps)``.  Files are written to *output_dir*
      (defaults to ``Path("output")``).
    - ``InputMode.SINGLE_FLOW`` → calls :func:`generate_single_flow_workflow`
      for the first flow and returns ``(workflow_dict, gaps)``.  No files
      are written.

    Args:
        ir: The intermediate representation.
        output_dir: Output directory for project mode. Ignored in single-flow
            mode. Defaults to ``Path("output")`` when not provided.

    Returns:
        ``(ProjectArtifacts, gaps)`` in project mode or
        ``(workflow_dict, gaps)`` in single-flow mode.
    """
    if ir.ir_metadata.source_mode == InputMode.PROJECT:
        effective_dir = output_dir or Path("output")
        return generate_project(ir, effective_dir)

    # Single-flow mode — no file I/O
    if ir.flows:
        return generate_single_flow_workflow(ir.flows[0])

    # No flows in single-flow IR — return a valid empty workflow
    return dict(_EMPTY_WORKFLOW), []
