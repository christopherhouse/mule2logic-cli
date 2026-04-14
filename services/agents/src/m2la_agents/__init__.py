"""Agent orchestration layer for MuleSoft to Logic Apps migration.

This package implements **multi-agent orchestration** using the
`Microsoft Agent Framework <https://github.com/microsoft/agent-framework>`_
(``agent-framework-core``).

In **online mode** (chat client provided), agents are constructed as MAF
``Agent`` instances and composed into a ``SequentialBuilder`` workflow
for LLM-backed multi-agent orchestration.

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
    analyzer_prompt,
    orchestrator_prompt,
    planner_prompt,
    repair_advisor_prompt,
    transformer_prompt,
    validator_prompt,
)
from m2la_agents.repair_advisor import RepairAdvisorAgent, RepairSuggestion
from m2la_agents.sdk_config import FoundryClientConfig
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
    # Config
    "FoundryClientConfig",
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
    "analyzer_prompt",
    "orchestrator_prompt",
    "planner_prompt",
    "repair_advisor_prompt",
    "transformer_prompt",
    "validator_prompt",
]
