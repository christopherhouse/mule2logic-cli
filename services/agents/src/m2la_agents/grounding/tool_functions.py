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
import time

from opentelemetry import metrics, trace

from m2la_agents.grounding.context7 import Context7Client
from m2la_agents.grounding.microsoft_learn import MicrosoftLearnClient

logger = logging.getLogger(__name__)

_tracer = trace.get_tracer("m2la.grounding")
_meter = metrics.get_meter("m2la.grounding")
_grounding_calls = _meter.create_counter("m2la.grounding.calls", description="Grounding API calls", unit="1")
_grounding_latency = _meter.create_histogram(
    "m2la.grounding.latency_ms", description="Grounding call latency in ms", unit="ms"
)

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
    start = time.monotonic()
    try:
        with _tracer.start_as_current_span("m2la.grounding.microsoft_learn") as span:
            span.set_attribute("provider", "microsoft_learn")
            span.set_attribute("query.length", len(query))
            client = _get_ms_learn_client()
            response = client.search(f"Azure Logic Apps Standard {query}")
            elapsed = (time.monotonic() - start) * 1000
            _grounding_calls.add(1, {"provider": "microsoft_learn", "status": "success"})
            _grounding_latency.record(elapsed, {"provider": "microsoft_learn"})
            return response.model_dump_json()
    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        _grounding_calls.add(1, {"provider": "microsoft_learn", "status": "error"})
        _grounding_latency.record(elapsed, {"provider": "microsoft_learn"})
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
    start = time.monotonic()
    try:
        with _tracer.start_as_current_span("m2la.grounding.microsoft_learn_fetch") as span:
            span.set_attribute("provider", "microsoft_learn")
            span.set_attribute("url.host", "learn.microsoft.com")
            client = _get_ms_learn_client()
            response = client.fetch_page(url)
            elapsed = (time.monotonic() - start) * 1000
            _grounding_calls.add(1, {"provider": "microsoft_learn", "status": "success"})
            _grounding_latency.record(elapsed, {"provider": "microsoft_learn"})
            return response.model_dump_json()
    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        _grounding_calls.add(1, {"provider": "microsoft_learn", "status": "error"})
        _grounding_latency.record(elapsed, {"provider": "microsoft_learn"})
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
    start = time.monotonic()
    try:
        with _tracer.start_as_current_span("m2la.grounding.context7") as span:
            span.set_attribute("provider", "context7")
            span.set_attribute("query.length", len(query))
            span.set_attribute("library", library)
            client = _get_context7_client()
            library_id = Context7Client.MULESOFT_LIBRARIES.get(library)
            response = client.get_documentation(query, library_id=library_id)
            elapsed = (time.monotonic() - start) * 1000
            _grounding_calls.add(1, {"provider": "context7", "status": "success"})
            _grounding_latency.record(elapsed, {"provider": "context7"})
            return response.model_dump_json()
    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        _grounding_calls.add(1, {"provider": "context7", "status": "error"})
        _grounding_latency.record(elapsed, {"provider": "context7"})
        logger.exception("search_mulesoft_docs failed for query: %r, library: %r", query, library)
        return json.dumps({"query": query, "provider": "context7", "results": [], "error": "Search failed"})
