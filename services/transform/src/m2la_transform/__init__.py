"""Logic Apps Standard project generator for MuleSoft to Logic Apps migration."""

from __future__ import annotations

from m2la_transform.generator import generate_project
from m2la_transform.models import ProjectArtifacts
from m2la_transform.single_flow import generate, generate_single_flow_workflow
from m2la_transform.workflow_generator import convert_dataweave_expression, generate_workflow

__all__ = [
    "ProjectArtifacts",
    "convert_dataweave_expression",
    "generate",
    "generate_project",
    "generate_single_flow_workflow",
    "generate_workflow",
]
