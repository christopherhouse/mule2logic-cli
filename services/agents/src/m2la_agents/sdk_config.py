"""Configuration for the Azure AI Agents SDK.

Provides :class:`AgentsClientConfig` to configure the connection to the
Azure AI Agents Service.  When ``endpoint`` is ``None``, agents run in
**offline / local mode** — deterministic logic only, no LLM calls.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentsClientConfig(BaseModel):
    """Configuration for connecting to the Azure AI Agents Service.

    When ``endpoint`` is ``None``, agents run in offline/local mode —
    deterministic logic only, no LLM calls.  This is the default for
    tests and CI environments.
    """

    endpoint: str | None = Field(
        default=None,
        description="Azure AI Foundry project endpoint (e.g. https://<project>.api.azureml.ms)",
    )
    model_deployment: str = Field(
        default="gpt-4o",
        description="Model deployment name for agent LLM backing",
    )
    # ``credential`` is not serializable and is handled separately at
    # runtime (e.g. via ``DefaultAzureCredential``).
