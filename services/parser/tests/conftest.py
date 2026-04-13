"""Shared pytest fixtures for the MuleSoft parser test suite."""

from pathlib import Path

import pytest

# Locate sample-projects relative to *this* test file so the suite works
# regardless of the working directory used when invoking pytest.
_SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "sample-projects"


@pytest.fixture()
def sample_projects_dir() -> Path:
    """Return the absolute path to the ``packages/sample-projects/`` directory."""
    assert _SAMPLES_DIR.is_dir(), f"Sample projects directory not found: {_SAMPLES_DIR}"
    return _SAMPLES_DIR


@pytest.fixture()
def hello_world_project(sample_projects_dir: Path) -> Path:
    """Return the absolute path to the hello-world-project sample."""
    project = sample_projects_dir / "hello-world-project"
    assert project.is_dir(), f"hello-world-project not found: {project}"
    return project


@pytest.fixture()
def standalone_flow_xml(sample_projects_dir: Path) -> Path:
    """Return the absolute path to ``standalone-flow.xml``."""
    xml = sample_projects_dir / "standalone-flow.xml"
    assert xml.is_file(), f"standalone-flow.xml not found: {xml}"
    return xml


@pytest.fixture()
def malformed_flow_xml(sample_projects_dir: Path) -> Path:
    """Return the absolute path to ``malformed-flow.xml``."""
    xml = sample_projects_dir / "malformed-flow.xml"
    assert xml.is_file(), f"malformed-flow.xml not found: {xml}"
    return xml


@pytest.fixture()
def empty_flow_xml(sample_projects_dir: Path) -> Path:
    """Return the absolute path to ``empty-flow.xml``."""
    xml = sample_projects_dir / "empty-flow.xml"
    assert xml.is_file(), f"empty-flow.xml not found: {xml}"
    return xml
