"""Agent orchestration layer for MuleSoft to Logic Apps migration.

This package provides thin orchestration wrappers (agents) around the
deterministic migration services.  Agents do **not** replace the services;
they compose them into a structured pipeline with correlation IDs,
telemetry propagation, and human-readable reasoning summaries.

When an ``AgentsClient`` is provided, agents are created on the Azure AI
Agent Service and runs use LLM-backed reasoning.  When no client is
provided (the default), agents run in **offline mode** — each agent's
deterministic ``execute()`` method is called directly.
"""

from m2la_agents.analyzer import AnalyzerAgent
from m2la_agents.base import BaseAgent
from m2la_agents.function_tools import (
    analyze_mule_input,
    create_migration_plan,
    suggest_repairs,
    transform_to_logic_apps,
    validate_output_artifacts,
)
from m2la_agents.models import AgentContext, AgentResult, AgentStatus, MigrationPlan, OrchestrationResult, StepResult
from m2la_agents.orchestrator import MigrationOrchestrator
from m2la_agents.planner import PlannerAgent
from m2la_agents.repair_advisor import RepairAdvisorAgent, RepairSuggestion
from m2la_agents.sdk_config import AgentsClientConfig
from m2la_agents.transformer import TransformerAgent
from m2la_agents.validator import ValidatorAgent

__all__ = [
    # Base
    "AgentStatus",
    "BaseAgent",
    # Models
    "AgentContext",
    "AgentResult",
    "MigrationPlan",
    "OrchestrationResult",
    "RepairSuggestion",
    "StepResult",
    # SDK config
    "AgentsClientConfig",
    # Agents
    "AnalyzerAgent",
    "PlannerAgent",
    "TransformerAgent",
    "ValidatorAgent",
    "RepairAdvisorAgent",
    # Orchestrator
    "MigrationOrchestrator",
    # Function tools
    "analyze_mule_input",
    "create_migration_plan",
    "transform_to_logic_apps",
    "validate_output_artifacts",
    "suggest_repairs",
]
