"""Shared pytest fixtures for the agent orchestration test suite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from m2la_agents.models import AgentContext

# Locate sample-projects relative to *this* test file so the suite works
# regardless of the working directory used when invoking pytest.
_SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages" / "sample-projects"


# ---------------------------------------------------------------------------
# Sample project fixtures
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Agent context fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def make_context() -> Any:
    """Factory fixture that creates an :class:`AgentContext` with defaults."""

    def _factory(
        input_path: str = "/fake/path",
        *,
        correlation_id: str = "test-correlation-id",
        input_mode: Any = None,
        output_directory: str | None = None,
        accumulated_data: dict[str, Any] | None = None,
    ) -> AgentContext:
        return AgentContext(
            correlation_id=correlation_id,
            trace_id="test-trace-id",
            span_id="test-span-id",
            input_mode=input_mode,
            input_path=input_path,
            output_directory=output_directory,
            accumulated_data=accumulated_data or {},
        )

    return _factory


@pytest.fixture()
def sample_ir() -> Any:
    """Build a minimal MuleIR for tests that need an IR without parsing real files."""
    from m2la_ir.builders import build_project_ir, make_flow, make_http_trigger, make_logger

    return build_project_ir(
        source_path="/fake/project",
        project_name="test-project",
        flows=[
            make_flow(
                name="helloFlow",
                trigger=make_http_trigger(path="/hello"),
                steps=[
                    make_logger(message="Hello World"),
                ],
            ),
        ],
    )


@pytest.fixture()
def sample_single_flow_ir() -> Any:
    """Build a minimal single-flow MuleIR."""
    from m2la_ir.builders import build_single_flow_ir, make_flow, make_http_trigger, make_logger

    return build_single_flow_ir(
        source_path="/fake/standalone.xml",
        flows=[
            make_flow(
                name="standaloneFlow",
                trigger=make_http_trigger(path="/api"),
                steps=[
                    make_logger(message="standalone"),
                ],
            ),
        ],
    )
