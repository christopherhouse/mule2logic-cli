"""MAF-compatible tool functions for documentation grounding.

These functions follow the same pattern as
:mod:`m2la_agents.function_tools` — plain Python functions with
JSON-serializable parameters that return JSON strings.  They are
registered on MAF ``Agent`` instances via ``tools=[...]``.

Tool functions never raise exceptions to the caller; grounding
failures are captured in the ``error`` field of the returned JSON.
"""

from __future__ import annotations

import json
import logging

from m2la_agents.grounding.context7 import Context7Client
from m2la_agents.grounding.microsoft_learn import MicrosoftLearnClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-initialised singleton clients
# ---------------------------------------------------------------------------

_ms_learn_client: MicrosoftLearnClient | None = None
_context7_client: Context7Client | None = None


def _get_ms_learn_client() -> MicrosoftLearnClient:
    """Return the module-level :class:`MicrosoftLearnClient`, creating it on first use."""
    global _ms_learn_client  # noqa: PLW0603
    if _ms_learn_client is None:
        _ms_learn_client = MicrosoftLearnClient()
    return _ms_learn_client


def _get_context7_client() -> Context7Client:
    """Return the module-level :class:`Context7Client`, creating it on first use."""
    global _context7_client  # noqa: PLW0603
    if _context7_client is None:
        _context7_client = Context7Client()
    return _context7_client


def _reset_clients() -> None:
    """Reset singleton clients.  **For testing only.**"""
    global _ms_learn_client, _context7_client  # noqa: PLW0603
    _ms_learn_client = None
    _context7_client = None


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


def search_logic_apps_docs(query: str) -> str:
    """Search Microsoft Learn for Azure Logic Apps documentation.

    Use this tool when you need information about Logic Apps Standard
    workflow definitions, connectors, triggers, actions, or expressions.

    Args:
        query: Search query about Logic Apps (e.g. "HTTP trigger
            workflow definition", "Service Bus connector authentication").

    Returns:
        JSON string with search results containing title, url, content,
        and source.
    """
    try:
        client = _get_ms_learn_client()
        response = client.search(f"Azure Logic Apps Standard {query}")
        return response.model_dump_json()
    except Exception:
        logger.exception("search_logic_apps_docs failed for query: %r", query)
        return json.dumps({"query": query, "provider": "microsoft_learn", "results": [], "error": "Search failed"})


def fetch_logic_apps_doc(url: str) -> str:
    """Fetch a specific Microsoft Learn documentation page.

    Use this tool to get the full content of a documentation page found
    via :func:`search_logic_apps_docs`.

    Args:
        url: Full URL of a Microsoft Learn page.

    Returns:
        JSON string with the page content.
    """
    try:
        client = _get_ms_learn_client()
        response = client.fetch_page(url)
        return response.model_dump_json()
    except Exception:
        logger.exception("fetch_logic_apps_doc failed for url: %s", url)
        return json.dumps({"query": url, "provider": "microsoft_learn", "results": [], "error": "Fetch failed"})


def search_mulesoft_docs(query: str, library: str = "connectors") -> str:
    """Search MuleSoft documentation for connector and construct details.

    Use this tool when you need information about MuleSoft connectors,
    DataWeave expressions, or Mule runtime behavior.

    Args:
        query: Search query about MuleSoft (e.g. "HTTP listener
            configuration", "scatter-gather router").
        library: MuleSoft documentation library to search.  Options:
            ``"connectors"`` (default), ``"dataweave"``, ``"general"``,
            ``"api-manager"``, ``"mule-sdk"``.

    Returns:
        JSON string with documentation content from Context7.
    """
    try:
        client = _get_context7_client()
        library_id = Context7Client.MULESOFT_LIBRARIES.get(library)
        response = client.get_documentation(query, library_id=library_id)
        return response.model_dump_json()
    except Exception:
        logger.exception("search_mulesoft_docs failed for query: %r, library: %r", query, library)
        return json.dumps({"query": query, "provider": "context7", "results": [], "error": "Search failed"})
