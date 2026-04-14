"""Configuration for the Microsoft Agent Framework client.

Provides :class:`FoundryClientConfig` to configure the connection to the
Azure AI Foundry Agent Service.  When ``endpoint`` is ``None``, agents run
in **offline mode** — deterministic logic only, no LLM calls.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FoundryClientConfig(BaseModel):
    """Configuration for connecting to Azure AI Foundry via the Microsoft Agent Framework.

    When ``endpoint`` is ``None``, agents run in offline/local mode —
    deterministic logic only, no LLM calls.  This is the default for
    tests and CI environments.
    """

    endpoint: str | None = Field(
        default=None,
        description="Azure AI Foundry project endpoint",
    )
    model: str = Field(
        default="gpt-4o",
        description="Model deployment name for agent LLM backing",
    )
