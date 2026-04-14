"""Custom OpenTelemetry metrics for the m2la platform.

This module exposes shared metric instruments created from a shared meter.
Service code can ``import`` them without requiring the full OTel SDK to be
installed because the ``opentelemetry-api`` package provides no-op stubs.
"""

from __future__ import annotations

from opentelemetry import metrics

_meter = metrics.get_meter("m2la-api", "0.1.0")

# ---------------------------------------------------------------------------
# Pipeline / Request Metrics
# ---------------------------------------------------------------------------

pipeline_requests = _meter.create_counter(
    name="m2la.pipeline.requests",
    description="Total pipeline invocations",
    unit="1",
)

pipeline_duration = _meter.create_histogram(
    name="m2la.pipeline.duration_ms",
    description="End-to-end pipeline duration in milliseconds",
    unit="ms",
)

pipeline_active = _meter.create_up_down_counter(
    name="m2la.pipeline.active",
    description="Currently in-flight pipelines",
    unit="1",
)

# ---------------------------------------------------------------------------
# Agent Metrics
# ---------------------------------------------------------------------------

agent_invocations = _meter.create_counter(
    name="m2la.agent.invocations",
    description="Per-agent invocation count",
    unit="1",
)

agent_duration = _meter.create_histogram(
    name="m2la.agent.duration_ms",
    description="Per-agent execution duration in milliseconds",
    unit="ms",
)

agent_errors = _meter.create_counter(
    name="m2la.agent.errors",
    description="Agent error count",
    unit="1",
)

# ---------------------------------------------------------------------------
# LLM / Token Metrics
# ---------------------------------------------------------------------------

llm_estimated_prompt_tokens = _meter.create_counter(
    name="m2la.llm.estimated_prompt_tokens",
    description="Estimated prompt tokens via tiktoken (pre-call)",
    unit="token",
)

llm_estimated_completion_tokens = _meter.create_counter(
    name="m2la.llm.estimated_completion_tokens",
    description="Estimated completion tokens via tiktoken (post-call)",
    unit="token",
)

llm_actual_prompt_tokens = _meter.create_counter(
    name="m2la.llm.actual_prompt_tokens",
    description="Actual prompt tokens from LLM API response",
    unit="token",
)

llm_actual_completion_tokens = _meter.create_counter(
    name="m2la.llm.actual_completion_tokens",
    description="Actual completion tokens from LLM API response",
    unit="token",
)

llm_actual_total_tokens = _meter.create_counter(
    name="m2la.llm.actual_total_tokens",
    description="Actual total tokens from LLM API response",
    unit="token",
)

llm_calls = _meter.create_counter(
    name="m2la.llm.calls",
    description="Total LLM API calls",
    unit="1",
)

llm_latency = _meter.create_histogram(
    name="m2la.llm.latency_ms",
    description="LLM call latency in milliseconds",
    unit="ms",
)

# ---------------------------------------------------------------------------
# Validation Metrics
# ---------------------------------------------------------------------------

validation_issues = _meter.create_counter(
    name="m2la.validation.issues",
    description="Validation issues detected",
    unit="1",
)

validation_runs = _meter.create_counter(
    name="m2la.validation.runs",
    description="Validation runs",
    unit="1",
)

# ---------------------------------------------------------------------------
# Transform Metrics
# ---------------------------------------------------------------------------

transform_workflows_generated = _meter.create_counter(
    name="m2la.transform.workflows_generated",
    description="Total workflows generated",
    unit="1",
)

transform_migration_gaps = _meter.create_counter(
    name="m2la.transform.migration_gaps",
    description="Migration gaps encountered",
    unit="1",
)

transform_artifacts_generated = _meter.create_counter(
    name="m2la.transform.artifacts_generated",
    description="Total artifact files generated",
    unit="1",
)

# ---------------------------------------------------------------------------
# Parser Metrics
# ---------------------------------------------------------------------------

parser_flows_parsed = _meter.create_counter(
    name="m2la.parser.flows_parsed",
    description="Total flows parsed",
    unit="1",
)

parser_constructs_parsed = _meter.create_counter(
    name="m2la.parser.constructs_parsed",
    description="Total constructs/processors parsed",
    unit="1",
)

parser_warnings = _meter.create_counter(
    name="m2la.parser.warnings",
    description="Parser warnings emitted",
    unit="1",
)

# ---------------------------------------------------------------------------
# Grounding Metrics
# ---------------------------------------------------------------------------

grounding_calls = _meter.create_counter(
    name="m2la.grounding.calls",
    description="Grounding API calls",
    unit="1",
)

grounding_latency = _meter.create_histogram(
    name="m2la.grounding.latency_ms",
    description="Grounding call latency in milliseconds",
    unit="ms",
)
