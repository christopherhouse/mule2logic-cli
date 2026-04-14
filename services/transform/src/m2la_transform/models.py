"""Pydantic models representing Logic Apps Standard project artifacts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowTrigger(BaseModel):
    """A Logic Apps workflow trigger definition."""

    type: str
    inputs: dict[str, Any]
    kind: str | None = None
    recurrence: dict[str, Any] | None = None


class WorkflowAction(BaseModel):
    """A single Logic Apps workflow action."""

    type: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    runAfter: dict[str, list[str]] = Field(default_factory=dict)


class WorkflowDefinition(BaseModel):
    """The inner definition block of a workflow.json file."""

    model_config = ConfigDict(populate_by_name=True)

    schema_: str = Field(
        default="https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        alias="$schema",
    )
    contentVersion: str = "1.0.0.0"
    triggers: dict[str, Any] = Field(default_factory=dict)
    actions: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)


class WorkflowFile(BaseModel):
    """Represents a complete workflow.json file."""

    definition: dict[str, Any]
    kind: str = "Stateful"


class ProjectArtifacts(BaseModel):
    """All generated artifacts for a full project conversion."""

    host_json: dict[str, Any]
    connections_json: dict[str, Any]
    parameters_json: dict[str, Any]
    env_content: str
    workflows: dict[str, dict[str, Any]]  # workflow_name -> workflow.json content
