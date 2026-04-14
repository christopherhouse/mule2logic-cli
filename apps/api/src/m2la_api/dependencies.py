"""FastAPI dependency injection for Foundry client and MigrationOrchestrator.

The ``get_chat_client`` dependency creates a ``FoundryChatClient`` on first
use (cached for the process lifetime).  Routes receive an orchestrator via
``get_orchestrator`` which wraps the shared chat client.

For tests, override ``get_chat_client`` in ``app.dependency_overrides`` to
inject a ``MockChatClient`` instead.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from m2la_api.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_chat_client() -> Any:
    """Return a cached ``FoundryChatClient`` (or compatible).

    Reads ``M2LA_FOUNDRY_ENDPOINT`` and ``M2LA_FOUNDRY_MODEL`` from
    application settings.  Uses ``DefaultAzureCredential`` for UAMI-based
    authentication.

    Raises :class:`RuntimeError` if the Foundry endpoint is not configured.
    """
    settings = get_settings()
    if not settings.foundry_endpoint:
        msg = (
            "M2LA_FOUNDRY_ENDPOINT is not configured. "
            "Set the environment variable to the Azure AI Foundry project endpoint."
        )
        logger.error(msg)
        raise RuntimeError(msg)

    from agent_framework.foundry import FoundryChatClient
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    client = FoundryChatClient(
        project_endpoint=settings.foundry_endpoint,
        model=settings.foundry_model,
        credential=credential,
    )
    logger.info(
        "FoundryChatClient created (endpoint=%s, model=%s)",
        settings.foundry_endpoint,
        settings.foundry_model,
    )
    return client
