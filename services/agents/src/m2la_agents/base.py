"""Base agent protocol using the Azure AI Agents SDK.

Each agent wraps an SDK ``Agent`` object created via
``AgentsClient.create_agent()``.  When running in **offline mode**
(no ``AgentsClient``), agents execute deterministic logic directly
without LLM involvement.

All agents extend :class:`BaseAgent` and implement:

* :meth:`_register_tools` — register deterministic service functions
  as :class:`~azure.ai.agents.models.FunctionTool` callables.
* :meth:`execute` — the offline / deterministic execution path.

The base class provides SDK lifecycle helpers
(:meth:`create_on_service`, :meth:`as_connected_agent_tool`,
:meth:`cleanup`) and a standardised ``execute(context) → AgentResult``
contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from azure.ai.agents.models import ToolSet

from m2la_agents.models import AgentContext, AgentResult

if TYPE_CHECKING:
    from azure.ai.agents import AgentsClient
    from azure.ai.agents.models import ConnectedAgentTool


class BaseAgent(ABC):
    """Abstract base class for migration agents using Azure AI Agents SDK.

    Each agent registers deterministic service functions as
    :class:`~azure.ai.agents.models.FunctionTool` callables via the SDK.
    When an ``AgentsClient`` is provided, agents are created on the Azure
    AI Agent Service and runs use LLM-backed reasoning.  When no client
    is provided (**offline mode**), agents execute their deterministic
    logic directly.

    In **online mode** the orchestrator wires sub-agents as
    :class:`~azure.ai.agents.models.ConnectedAgentTool` definitions
    attached to a main orchestrator agent, enabling true multi-agent
    delegation via the Azure AI Agent Service.

    Attributes:
        name: Human-readable agent name (e.g. ``"AnalyzerAgent"``).
        instructions: Agent system prompt / instructions for the LLM.
        toolset: SDK ``ToolSet`` with registered ``FunctionTool`` callables.
        sdk_agent_id: ID of the agent created on the service
            (``None`` in offline mode).
    """

    name: str
    instructions: str
    toolset: ToolSet
    sdk_agent_id: str | None

    def __init__(self, *, name: str, instructions: str = "") -> None:
        self.name = name
        self.instructions = instructions
        self.toolset = ToolSet()
        self.sdk_agent_id = None
        self._register_tools()

    # ------------------------------------------------------------------
    # Tool registration (subclass hook)
    # ------------------------------------------------------------------

    @abstractmethod
    def _register_tools(self) -> None:
        """Register deterministic service functions as ``FunctionTool`` in *self.toolset*."""
        ...

    # ------------------------------------------------------------------
    # SDK lifecycle
    # ------------------------------------------------------------------

    def create_on_service(self, client: AgentsClient, model: str) -> str:
        """Create this agent on the Azure AI Agent Service.

        Args:
            client: An authenticated ``AgentsClient``.
            model: The model deployment name (e.g. ``"gpt-4o"``).

        Returns:
            The agent ID assigned by the service.
        """
        sdk_agent = client.create_agent(
            model=model,
            name=self.name,
            instructions=self.instructions,
            toolset=self.toolset,
        )
        self.sdk_agent_id = sdk_agent.id
        return sdk_agent.id

    def as_connected_agent_tool(self, description: str) -> ConnectedAgentTool:
        """Return a :class:`ConnectedAgentTool` definition for this agent.

        This allows the orchestrator to wire this agent as a **sub-agent**
        that the main orchestrator agent can delegate tasks to via the
        Azure AI Agent Service.

        Args:
            description: A short description of when this sub-agent
                should be invoked (used by the LLM for routing).

        Returns:
            A ``ConnectedAgentTool`` suitable for passing to
            ``create_agent(tools=...)``.

        Raises:
            RuntimeError: If the agent has not been created on the
                service yet (``sdk_agent_id is None``).
        """
        from azure.ai.agents.models import ConnectedAgentTool

        if self.sdk_agent_id is None:
            msg = f"{self.name} has not been created on the service yet. Call create_on_service() first."
            raise RuntimeError(msg)

        return ConnectedAgentTool(
            id=self.sdk_agent_id,
            name=self.name,
            description=description,
        )

    def cleanup(self, client: AgentsClient) -> None:
        """Delete this agent from the service."""
        if self.sdk_agent_id:
            client.delete_agent(self.sdk_agent_id)
            self.sdk_agent_id = None

    # ------------------------------------------------------------------
    # Execution (offline / deterministic path)
    # ------------------------------------------------------------------

    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """Run the agent's orchestration logic (offline/deterministic mode).

        This is the single entry point for every agent when running
        **without** the Azure AI Agent Service.  Implementations should:

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
        mode = "online" if self.sdk_agent_id else "offline"
        return f"{type(self).__name__}(name={self.name!r}, mode={mode})"
