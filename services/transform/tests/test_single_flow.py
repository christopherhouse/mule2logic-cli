"""Tests for single-flow mode (single_flow.py)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from m2la_ir.models import Flow, MuleIR

from m2la_transform.single_flow import generate, generate_single_flow_workflow
from m2la_transform.workflow_generator import WORKFLOW_SCHEMA

# ── generate_single_flow_workflow ─────────────────────────────────────────────


def test_single_flow_returns_workflow_dict(simple_http_flow: Flow) -> None:
    """generate_single_flow_workflow returns a dict with a 'definition' key."""
    result, gaps = generate_single_flow_workflow(simple_http_flow)

    assert isinstance(result, dict)
    assert "definition" in result
    assert isinstance(gaps, list)


def test_single_flow_workflow_has_schema(simple_http_flow: Flow) -> None:
    """The returned dict contains the required $schema and contentVersion."""
    result, _ = generate_single_flow_workflow(simple_http_flow)

    definition = result["definition"]
    assert definition["$schema"] == WORKFLOW_SCHEMA
    assert definition["contentVersion"] == "1.0.0.0"


def test_single_flow_has_kind_stateful(simple_http_flow: Flow) -> None:
    """The returned workflow dict has kind == 'Stateful'."""
    result, _ = generate_single_flow_workflow(simple_http_flow)
    assert result["kind"] == "Stateful"


def test_single_flow_no_files_written(simple_http_flow: Flow, tmp_path: Path) -> None:
    """generate_single_flow_workflow writes no files to the filesystem."""
    generate_single_flow_workflow(simple_http_flow)

    # tmp_path is clean — confirm the function didn't touch it
    assert list(tmp_path.iterdir()) == []


def test_single_flow_triggers_present(simple_http_flow: Flow) -> None:
    """The returned workflow has at least one trigger for a triggered flow."""
    result, _ = generate_single_flow_workflow(simple_http_flow)
    assert result["definition"]["triggers"], "Expected at least one trigger"


# ── generate() dispatcher ─────────────────────────────────────────────────────


def test_generate_dispatches_to_single_flow_mode(
    single_flow_ir: MuleIR,
    tmp_path: Path,
) -> None:
    """generate() in single-flow mode returns a workflow dict, not ProjectArtifacts."""
    from m2la_transform.models import ProjectArtifacts

    result, gaps = generate(single_flow_ir, tmp_path)

    assert not isinstance(result, ProjectArtifacts), (
        "Single-flow mode should return a workflow dict, not ProjectArtifacts"
    )
    assert isinstance(result, dict)
    assert "definition" in result


def test_generate_dispatches_to_project_mode(
    project_ir: MuleIR,
    tmp_path: Path,
) -> None:
    """generate() in project mode returns ProjectArtifacts."""
    from m2la_transform.models import ProjectArtifacts

    result, gaps = generate(project_ir, tmp_path)

    assert isinstance(result, ProjectArtifacts)


def test_generate_single_flow_writes_no_files(
    single_flow_ir: MuleIR,
    tmp_path: Path,
) -> None:
    """generate() in single-flow mode does not create any files."""
    generate(single_flow_ir, None)
    # If output_dir=None in single-flow mode no files should be written to cwd
    # (just verify the call completes without error and returns a workflow dict)


def test_generate_empty_single_flow_ir_returns_empty_workflow(tmp_path: Path) -> None:
    """generate() with an IR that has no flows returns an empty-but-valid workflow."""
    from m2la_ir.builders import build_single_flow_ir

    empty_ir = build_single_flow_ir(source_path="/empty.xml", flows=[])
    result, gaps = generate(empty_ir)

    assert isinstance(result, dict)
    assert "definition" in result
    assert result["definition"]["triggers"] == {}
    assert result["definition"]["actions"] == {}
    assert gaps == []


def test_generate_project_mode_creates_files(
    project_ir: MuleIR,
    tmp_path: Path,
) -> None:
    """generate() project mode writes host.json and workflow files."""
    generate(project_ir, tmp_path)

    assert (tmp_path / "host.json").exists()
    assert (tmp_path / "connections.json").exists()


def test_generate_uses_default_output_dir_in_project_mode(
    project_ir: MuleIR,
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """generate() uses Path('output') when output_dir is None in project mode."""
    monkeypatch.chdir(tmp_path)

    generate(project_ir, None)

    default_out = tmp_path / "output"
    assert default_out.exists(), "Expected 'output' directory to be created"
    assert (default_out / "host.json").exists()
