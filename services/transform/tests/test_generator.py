"""Tests for the project-mode generator (generator.py)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from m2la_ir.models import MuleIR

from m2la_transform.generator import generate_project

# ── helpers ───────────────────────────────────────────────────────────────────


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── file-layout tests ─────────────────────────────────────────────────────────


def test_generate_project_creates_expected_files(
    project_ir: MuleIR,
    tmp_path: Path,
) -> None:
    """All expected top-level files and workflow directories are created."""
    generate_project(project_ir, tmp_path)

    assert (tmp_path / "host.json").exists()
    assert (tmp_path / "connections.json").exists()
    assert (tmp_path / "parameters.json").exists()
    assert (tmp_path / ".env").exists()

    # At least one workflow directory with a workflow.json
    workflow_dirs = list((tmp_path / "workflows").iterdir())
    assert workflow_dirs, "Expected at least one workflow directory"
    for wf_dir in workflow_dirs:
        assert (wf_dir / "workflow.json").exists()


def test_workflow_files_created_for_each_flow(
    project_ir: MuleIR,
    tmp_path: Path,
) -> None:
    """One workflow sub-directory is created per flow in the IR."""
    artifacts, _ = generate_project(project_ir, tmp_path)

    workflow_dirs = {d.name for d in (tmp_path / "workflows").iterdir()}
    assert len(workflow_dirs) == len(project_ir.flows)
    assert len(artifacts.workflows) == len(project_ir.flows)


# ── host.json ─────────────────────────────────────────────────────────────────


def test_host_json_content(project_ir: MuleIR, tmp_path: Path) -> None:
    """host.json has the correct version and extensionBundle structure."""
    generate_project(project_ir, tmp_path)
    data = _load_json(tmp_path / "host.json")

    assert data["version"] == "2.0"
    bundle = data["extensionBundle"]
    assert bundle["id"] == "Microsoft.Azure.Functions.ExtensionBundle.Workflows"
    assert "version" in bundle


# ── connections.json ──────────────────────────────────────────────────────────


def test_connections_json_structure(project_ir: MuleIR, tmp_path: Path) -> None:
    """connections.json always has both top-level keys."""
    generate_project(project_ir, tmp_path)
    data = _load_json(tmp_path / "connections.json")

    assert "managedApiConnections" in data
    assert "serviceProviderConnections" in data
    assert isinstance(data["managedApiConnections"], dict)
    assert isinstance(data["serviceProviderConnections"], dict)


# ── parameters.json ───────────────────────────────────────────────────────────


def test_parameters_json_has_required_keys(project_ir: MuleIR, tmp_path: Path) -> None:
    """parameters.json always contains the two mandatory subscription/RG keys."""
    generate_project(project_ir, tmp_path)
    data = _load_json(tmp_path / "parameters.json")

    assert "WORKFLOWS_SUBSCRIPTION_ID" in data
    assert "WORKFLOWS_RESOURCE_GROUP" in data
    assert data["WORKFLOWS_SUBSCRIPTION_ID"]["type"] == "String"
    assert data["WORKFLOWS_RESOURCE_GROUP"]["type"] == "String"


# ── .env ──────────────────────────────────────────────────────────────────────

_ALL_ZEROS_UUID = "00000000-0000-0000-0000-000000000000"
_UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def test_env_has_required_vars(project_ir: MuleIR, tmp_path: Path) -> None:
    """The .env file contains all three mandatory variable names."""
    generate_project(project_ir, tmp_path)
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")

    assert "WORKFLOWS_SUBSCRIPTION_ID=" in env_text
    assert "WORKFLOWS_RESOURCE_GROUP=" in env_text
    assert "WORKFLOWS_MANAGED_IDENTITY_CLIENT_ID=" in env_text


def test_env_no_real_secrets(project_ir: MuleIR, tmp_path: Path) -> None:
    """Every UUID in the .env is the all-zeros placeholder — no real credentials."""
    generate_project(project_ir, tmp_path)
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")

    # Every UUID-shaped token must be the all-zeros placeholder
    for match in _UUID_PATTERN.finditer(env_text):
        assert match.group() == _ALL_ZEROS_UUID, f"Found non-placeholder UUID in .env: {match.group()}"

    # No obvious secret keywords
    assert "password" not in env_text.lower()
    assert "secret" not in env_text.lower()
    assert "connectionstring" not in env_text.lower().replace("_", "")


# ── determinism ───────────────────────────────────────────────────────────────


def test_deterministic_output(project_ir: MuleIR, tmp_path: Path) -> None:
    """Generating the same IR twice produces byte-identical output."""
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"

    generate_project(project_ir, out_a)
    generate_project(project_ir, out_b)

    for file_rel in ["host.json", "connections.json", "parameters.json", ".env"]:
        content_a = (out_a / file_rel).read_text(encoding="utf-8")
        content_b = (out_b / file_rel).read_text(encoding="utf-8")
        assert content_a == content_b, f"Non-deterministic output for {file_rel}"

    # Also compare workflow files
    for wf_dir_a in (out_a / "workflows").iterdir():
        wf_file_a = wf_dir_a / "workflow.json"
        wf_file_b = out_b / "workflows" / wf_dir_a.name / "workflow.json"
        assert wf_file_b.exists(), f"Missing workflow in second run: {wf_dir_a.name}"
        assert wf_file_a.read_text() == wf_file_b.read_text(), f"Non-deterministic workflow.json for {wf_dir_a.name}"


# ── return value ──────────────────────────────────────────────────────────────


def test_generate_project_returns_artifacts_and_gaps(
    project_ir: MuleIR,
    tmp_path: Path,
) -> None:
    """generate_project returns a (ProjectArtifacts, list[MigrationGap]) tuple."""
    from m2la_transform.models import ProjectArtifacts

    artifacts, gaps = generate_project(project_ir, tmp_path)

    assert isinstance(artifacts, ProjectArtifacts)
    assert isinstance(gaps, list)


@pytest.mark.parametrize("flow_idx", [0, 1])
def test_workflow_content_in_artifacts(
    project_ir: MuleIR,
    tmp_path: Path,
    flow_idx: int,
) -> None:
    """Each workflow dict in ProjectArtifacts has the definition and kind keys."""
    artifacts, _ = generate_project(project_ir, tmp_path)

    for wf_dict in artifacts.workflows.values():
        assert "definition" in wf_dict
        assert "kind" in wf_dict
