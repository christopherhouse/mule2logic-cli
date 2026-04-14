"""Base agent protocol and shared enumerations.

All agents extend :class:`BaseAgent` and implement the
:meth:`~BaseAgent.execute` method. The base class provides:

* A common ``name`` and ``tools`` interface.
* A standardised ``execute(context) → AgentResult`` contract.
* A clear separation between **deterministic service logic**
  (which lives in ``m2la_parser``, ``m2la_ir``, ``m2la_transform``, etc.)
  and **orchestration logic** (which lives here).

Agents are thin — they call deterministic services, measure timing,
and produce structured :class:`~m2la_agents.models.AgentResult` objects
with reasoning summaries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from m2la_agents.models import AgentContext, AgentResult


class AgentStatus(StrEnum):
    """Outcome status of an agent execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class BaseAgent(ABC):
    """Abstract base class for all migration agents.

    Subclasses must implement :meth:`execute`, which receives an
    :class:`AgentContext` and returns an :class:`AgentResult`.

    Attributes:
        name: Human-readable agent name (e.g. ``"AnalyzerAgent"``).
        tools: Placeholder list for future MCP tool definitions.
            Currently empty for all agents; the design allows
            future LLM-backed tool integrations without changing
            the protocol.
    """

    name: str
    tools: list[Any]

    def __init__(self, *, name: str, tools: list[Any] | None = None) -> None:
        self.name = name
        self.tools = tools or []

    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """Run the agent's orchestration logic.

        This is the single entry point for every agent. Implementations
        should:

        1. Extract required inputs from *context*.
        2. Call one or more deterministic services.
        3. Build and return a structured :class:`AgentResult`.

        Args:
            context: The current orchestration context carrying
                correlation IDs, input parameters, and any accumulated
                data from prior pipeline steps.

        Returns:
            An :class:`AgentResult` with status, output, and reasoning.
        """
        ...

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r}, tools={len(self.tools)})"
