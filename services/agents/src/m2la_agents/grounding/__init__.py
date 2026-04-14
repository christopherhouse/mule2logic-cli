"""Grounding providers for documentation-backed agent tool calls.

This package exposes HTTP clients and MAF-compatible tool functions that
ground agent reasoning in official Microsoft Learn and MuleSoft
documentation via the Context7 API.
"""

from __future__ import annotations

from m2la_agents.grounding.context7 import Context7Client
from m2la_agents.grounding.errors import GroundingConnectionError, GroundingError, GroundingTimeoutError
from m2la_agents.grounding.microsoft_learn import MicrosoftLearnClient
from m2la_agents.grounding.models import GroundingResponse, GroundingResult
from m2la_agents.grounding.tool_functions import (
    fetch_logic_apps_doc,
    search_logic_apps_docs,
    search_mulesoft_docs,
)

__all__ = [
    # Clients
    "Context7Client",
    "MicrosoftLearnClient",
    # Models
    "GroundingResponse",
    "GroundingResult",
    # Errors
    "GroundingConnectionError",
    "GroundingError",
    "GroundingTimeoutError",
    # Tool functions
    "fetch_logic_apps_doc",
    "search_logic_apps_docs",
    "search_mulesoft_docs",
]
