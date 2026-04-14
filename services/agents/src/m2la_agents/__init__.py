"""Agent orchestration layer for MuleSoft to Logic Apps migration.

This package provides thin orchestration wrappers (agents) around the
deterministic migration services. Agents do **not** replace the services;
they compose them into a structured pipeline with correlation IDs,
telemetry propagation, and human-readable reasoning summaries.

Current agents are purely deterministic. The design is extensible for
future Microsoft Agent Framework / MCP tool integrations by adding entries
to each agent's ``tools`` list.
"""

from m2la_agents.analyzer import AnalyzerAgent
from m2la_agents.base import BaseAgent
from m2la_agents.models import AgentContext, AgentResult, AgentStatus, MigrationPlan, OrchestrationResult, StepResult
from m2la_agents.orchestrator import MigrationOrchestrator
from m2la_agents.planner import PlannerAgent
from m2la_agents.repair_advisor import RepairAdvisorAgent, RepairSuggestion
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
    # Agents
    "AnalyzerAgent",
    "PlannerAgent",
    "TransformerAgent",
    "ValidatorAgent",
    "RepairAdvisorAgent",
    # Orchestrator
    "MigrationOrchestrator",
]
