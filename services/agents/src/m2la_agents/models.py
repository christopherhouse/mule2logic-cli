"""Shared Pydantic models for agent orchestration.

These models carry data through the migration pipeline:

* :class:`AgentContext` — inputs, correlation IDs, accumulated state.
* :class:`AgentResult` — structured output from a single agent step.
* :class:`StepResult` — timing wrapper around an :class:`AgentResult`.
* :class:`OrchestrationResult` — the full pipeline outcome.
* :class:`MigrationPlan` — the planner agent's structured output.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from m2la_contracts.enums import InputMode
from pydantic import BaseModel, Field


class AgentStatus(StrEnum):
    """Outcome status of an agent execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class AgentContext(BaseModel):
    """Context object threaded through the agent pipeline.

    Carries correlation IDs for observability, input parameters, and
    a mutable ``accumulated_data`` dict where each agent deposits its
    output for downstream agents to consume.
    """

    correlation_id: str = Field(..., description="Unique pipeline run ID (UUID)")
    trace_id: str = Field(default="", description="OpenTelemetry trace ID")
    span_id: str = Field(default="", description="OpenTelemetry span ID")
    input_mode: InputMode | None = Field(default=None, description="Input mode override (auto-detected if None)")
    input_path: str = Field(..., description="Path to MuleSoft project directory or flow XML file")
    output_directory: str | None = Field(default=None, description="Output directory for generated artifacts")
    accumulated_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Mutable state passed between agents. Keys are agent names or data labels.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (e.g. user options, feature flags).",
    )


class AgentResult(BaseModel):
    """Structured result returned by every agent.

    Contains the agent's output data, a human-readable reasoning summary,
    timing information, and any warnings or errors encountered.
    """

    agent_name: str = Field(..., description="Name of the agent that produced this result")
    status: AgentStatus = Field(..., description="Outcome status")
    output: Any = Field(default=None, description="Agent-specific output payload")
    reasoning_summary: str = Field(
        default="",
        description="Short human-readable summary of what the agent did and why",
    )
    duration_ms: float = Field(default=0.0, ge=0, description="Wall-clock duration in milliseconds")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings emitted during execution")
    error_message: str | None = Field(default=None, description="Error message if status is FAILURE")


class StepResult(BaseModel):
    """Timing and result wrapper for a single pipeline step."""

    step_name: str = Field(..., description="Name of the pipeline step (typically the agent name)")
    agent_result: AgentResult = Field(..., description="The agent's result")
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Step start timestamp")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Step completion timestamp")


class OrchestrationResult(BaseModel):
    """Full result of a migration orchestration pipeline run."""

    correlation_id: str = Field(..., description="Correlation ID for the entire pipeline run")
    steps: list[StepResult] = Field(default_factory=list, description="Results from each pipeline step in order")
    overall_status: AgentStatus = Field(..., description="Overall pipeline status")
    total_duration_ms: float = Field(default=0.0, ge=0, description="Total wall-clock duration in milliseconds")
    final_output: Any = Field(default=None, description="The final output from the last successful step")


class MappingDecision(BaseModel):
    """A single mapping decision for a construct or connector in the plan."""

    mule_element: str = Field(..., description="MuleSoft element name")
    status: str = Field(..., description="supported | unsupported | partial")
    logic_apps_equivalent: str | None = Field(default=None, description="Logic Apps equivalent, if known")
    notes: str | None = Field(default=None, description="Additional notes about the mapping")


class MigrationPlan(BaseModel):
    """Structured output from the :class:`PlannerAgent`.

    Summarises which MuleSoft constructs can be migrated, which cannot,
    and provides per-flow analysis with mapping decisions.
    """

    flow_count: int = Field(default=0, ge=0, description="Number of flows to migrate")
    construct_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Per-construct-type counts (e.g. {'http_listener': 2, 'logger': 3})",
    )
    supported_count: int = Field(default=0, ge=0, description="Number of fully supported constructs")
    unsupported_count: int = Field(default=0, ge=0, description="Number of unsupported constructs")
    partial_count: int = Field(default=0, ge=0, description="Number of partially supported constructs")
    mapping_decisions: list[MappingDecision] = Field(
        default_factory=list, description="Per-construct mapping decisions"
    )
    estimated_gaps: int = Field(default=0, ge=0, description="Estimated number of migration gaps")
