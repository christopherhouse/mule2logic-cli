"""Configuration for the Microsoft Agent Framework client.

Provides :class:`FoundryClientConfig` to configure the connection to the
Azure AI Foundry Agent Service.  The ``endpoint`` is **required** — the
LLM is the execution engine for all agent orchestration.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FoundryClientConfig(BaseModel):
    """Configuration for connecting to Azure AI Foundry via the Microsoft Agent Framework.

    Both ``endpoint`` and ``model`` must be set for production use.
    The ``endpoint`` has no default — callers must supply the Azure AI
    Foundry project URL.
    """

    endpoint: str = Field(
        ...,
        description="Azure AI Foundry project endpoint",
    )
    model: str = Field(
        default="gpt-4o",
        description="Model deployment name for agent LLM backing",
    )
