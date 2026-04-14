"""Agent orchestration layer for MuleSoft to Logic Apps migration.

This package implements **multi-agent orchestration** using the
`Azure AI Agents SDK <https://learn.microsoft.com/en-us/azure/ai-services/agents/>`_
(``azure-ai-agents``).

In **online mode** (``AgentsClient`` provided), the orchestrator creates
specialized sub-agents on the Azure AI Agent Service, wires them as
:class:`~azure.ai.agents.models.ConnectedAgentTool` definitions on a main
orchestrator agent, and runs the migration pipeline via threads + runs with
LLM-backed reasoning.

In **offline mode** (default, for tests/CI), each agent's deterministic
``execute()`` method is called directly — no LLM calls or network access.
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
from m2la_agents.prompts import (
    ANALYZER_PROMPT,
    ORCHESTRATOR_PROMPT,
    PLANNER_PROMPT,
    REPAIR_ADVISOR_PROMPT,
    TRANSFORMER_PROMPT,
    VALIDATOR_PROMPT,
)
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
    # Prompts
    "ANALYZER_PROMPT",
    "ORCHESTRATOR_PROMPT",
    "PLANNER_PROMPT",
    "REPAIR_ADVISOR_PROMPT",
    "TRANSFORMER_PROMPT",
    "VALIDATOR_PROMPT",
]
