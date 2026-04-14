"""Base agent protocol for the Microsoft Agent Framework integration.

Each concrete agent extends :class:`BaseAgent` and implements:

* :meth:`_get_tools` — return deterministic service functions to be
  registered as tools on the MAF ``Agent``.
* :meth:`execute` — direct execution of the agent's deterministic
  logic, used internally by tool functions.

The base class provides helpers for constructing a MAF ``Agent``
(:meth:`build_maf_agent`) and a standardised
``execute(context) → AgentResult`` contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

from m2la_agents.models import AgentContext, AgentResult

if TYPE_CHECKING:
    from agent_framework import Agent


class BaseAgent(ABC):
    """Abstract base class for migration agents.

    Each agent is backed by the LLM via the Microsoft Agent Framework.
    :meth:`build_maf_agent` constructs a MAF ``Agent`` instance with
    registered tool functions and domain-specific instructions.

    The :meth:`execute` method provides the underlying deterministic
    logic that tool functions wrap.  In production, ``execute()`` is
    only invoked through tool functions called by the LLM.

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
        """Construct a Microsoft Agent Framework ``Agent``.

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
    # Direct execution (used by tool functions)
    # ------------------------------------------------------------------

    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """Run the agent's deterministic logic directly.

        This method implements the core business logic that each
        agent's tool function wraps.  In production the LLM invokes
        tool functions which delegate here.

        Implementations should:

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
