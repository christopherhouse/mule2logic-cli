"""Base agent protocol for the Microsoft Agent Framework integration.

Each concrete agent extends :class:`BaseAgent` and implements:

* :meth:`_get_tools` — return deterministic service functions to be
  registered as tools on the MAF ``Agent``.
* :meth:`execute` — the offline / deterministic execution path used
  when no LLM client is available.

The base class provides helpers for constructing a MAF ``Agent``
(:meth:`build_maf_agent`) and a standardised
``execute(context) → AgentResult`` contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Sequence

from m2la_agents.models import AgentContext, AgentResult

if TYPE_CHECKING:
    from agent_framework import Agent


class BaseAgent(ABC):
    """Abstract base class for migration agents.

    Each agent can operate in two modes:

    * **Offline** (default) — :meth:`execute` is called directly with
      no LLM involvement.  All logic is deterministic.
    * **Online** — :meth:`build_maf_agent` constructs a Microsoft Agent
      Framework ``Agent`` backed by a chat client (e.g.
      ``FoundryChatClient``).  The LLM invokes the registered tool
      functions and provides reasoning on top.

    Attributes:
        name: Human-readable agent name (e.g. ``"AnalyzerAgent"``).
        instructions: System prompt loaded from a markdown file.
    """

    name: str
    instructions: str

    def __init__(self, *, name: str, instructions: str = "") -> None:
        self.name = name
        self.instructions = instructions

    # ------------------------------------------------------------------
    # Tool registration (subclass hook)
    # ------------------------------------------------------------------

    @abstractmethod
    def _get_tools(self) -> Sequence[Callable[..., Any]]:
        """Return deterministic service functions to register as tools."""
        ...

    # ------------------------------------------------------------------
    # MAF Agent construction
    # ------------------------------------------------------------------

    def build_maf_agent(self, client: Any) -> Agent:
        """Construct a Microsoft Agent Framework ``Agent`` for online mode.

        Args:
            client: A MAF chat client (e.g. ``FoundryChatClient`` or
                ``OpenAIChatClient``).

        Returns:
            An ``Agent`` instance ready for ``SequentialBuilder`` or
            direct ``agent.run()`` invocation.
        """
        from agent_framework import Agent

        return Agent(
            client=client,
            name=self.name,
            instructions=self.instructions,
            tools=list(self._get_tools()),
        )

    # ------------------------------------------------------------------
    # Execution (offline / deterministic path)
    # ------------------------------------------------------------------

    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """Run the agent's orchestration logic (offline/deterministic mode).

        This is the single entry point for every agent when running
        **without** an LLM client.  Implementations should:

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
        return f"{type(self).__name__}(name={self.name!r})"
