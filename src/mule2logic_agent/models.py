"""Shared data models for the mule2logic agent.

These models define the contract between the agent and any consumer
(CLI, REST API, container app, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Workflow definition types
# ---------------------------------------------------------------------------

# We use plain dicts for the JSON-heavy workflow structures.  TypedDicts
# give us documentation and type-checking at dev time without imposing
# runtime overhead on the large, variable-shape Logic Apps JSON.

WorkflowDefinition = dict[str, Any]
"""A Logic Apps workflow definition dict.  Guaranteed to have at minimum:
{
  "definition": {
    "triggers": { ... },
    "actions": { ... },
  }
}
"""


# ---------------------------------------------------------------------------
# Request / response models  (agent ↔ CLI / API boundary)
# ---------------------------------------------------------------------------

@dataclass
class ConvertRequest:
    """Input to the conversion agent."""

    xml: str
    """Raw MuleSoft XML to convert."""

    model: str = "gpt-4o"
    """Foundry model deployment name."""

    timeout: float = 300.0
    """Maximum seconds per agent call."""

    verbose: bool = False
    """Emit debug / trace information."""

    skip_review: bool = False
    """When True, skip the QC review agent step."""

    include_explanation: bool = False
    """When True, include the raw LLM explanation alongside the workflow."""

    generate_report: bool = False
    """When True, generate a migration-analysis Markdown report."""


@dataclass
class ConvertResult:
    """Output from the conversion agent."""

    workflow: WorkflowDefinition
    """The validated Logic Apps workflow JSON."""

    raw_response: str = ""
    """The raw text returned by the LLM (useful for --explain / --debug)."""

    review_issues: list[str] = field(default_factory=list)
    """Structural issues remaining after the QC review pass."""

    report: str = ""
    """Migration-analysis Markdown report (empty unless requested)."""
