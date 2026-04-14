"""Tests for the grounding provider package.

All HTTP calls are mocked — no real network traffic is generated.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from m2la_agents.grounding.context7 import Context7Client
from m2la_agents.grounding.errors import GroundingConnectionError, GroundingError, GroundingTimeoutError
from m2la_agents.grounding.microsoft_learn import MicrosoftLearnClient
from m2la_agents.grounding.models import GroundingResponse, GroundingResult
from m2la_agents.grounding.tool_functions import (
    _reset_clients,
    fetch_logic_apps_doc,
    search_logic_apps_docs,
    search_mulesoft_docs,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_tool_singletons() -> None:
    """Ensure tool-function singletons are reset between tests."""
    _reset_clients()
    yield  # type: ignore[misc]
    _reset_clients()


def _make_httpx_response(
    *,
    status_code: int = 200,
    json_body: dict[str, Any] | None = None,
    text_body: str | None = None,
    url: str = "https://example.com",
) -> httpx.Response:
    """Build a fake :class:`httpx.Response`."""
    resp = httpx.Response(
        status_code=status_code,
        request=httpx.Request("GET", url),
        json=json_body,
        text=text_body,
    )
    return resp


# ===================================================================
# Model tests
# ===================================================================


class TestGroundingResult:
    """Tests for :class:`GroundingResult`."""

    def test_minimal_construction(self) -> None:
        result = GroundingResult(title="T", url="https://example.com", content="C", source="test")
        assert result.title == "T"
        assert result.relevance_score == 0.0
        assert result.metadata == {}

    def test_full_construction(self) -> None:
        result = GroundingResult(
            title="Title",
            url="https://example.com",
            content="Body",
            source="microsoft_learn",
            relevance_score=0.95,
            metadata={"key": "value"},
        )
        assert result.relevance_score == 0.95
        assert result.metadata["key"] == "value"

    def test_json_round_trip(self) -> None:
        result = GroundingResult(title="T", url="u", content="c", source="s")
        data = json.loads(result.model_dump_json())
        rebuilt = GroundingResult.model_validate(data)
        assert rebuilt == result


class TestGroundingResponse:
    """Tests for :class:`GroundingResponse`."""

    def test_defaults(self) -> None:
        resp = GroundingResponse(query="q", provider="p")
        assert resp.results == []
        assert resp.duration_ms == 0.0
        assert resp.error is None
        assert resp.warnings == []

    def test_with_error(self) -> None:
        resp = GroundingResponse(query="q", provider="p", error="something broke")
        assert resp.error == "something broke"

    def test_json_round_trip(self) -> None:
        resp = GroundingResponse(
            query="q",
            provider="p",
            results=[GroundingResult(title="t", url="u", content="c", source="s")],
            duration_ms=42.5,
            warnings=["w1"],
        )
        data = json.loads(resp.model_dump_json())
        rebuilt = GroundingResponse.model_validate(data)
        assert rebuilt == resp


# ===================================================================
# Error hierarchy tests
# ===================================================================


class TestErrors:
    """Tests for grounding error types."""

    def test_timeout_is_grounding_error(self) -> None:
        assert issubclass(GroundingTimeoutError, GroundingError)

    def test_connection_is_grounding_error(self) -> None:
        assert issubclass(GroundingConnectionError, GroundingError)

    def test_base_error_message(self) -> None:
        err = GroundingError("msg")
        assert str(err) == "msg"


# ===================================================================
# MicrosoftLearnClient tests
# ===================================================================


_MS_LEARN_SEARCH_RESPONSE: dict[str, Any] = {
    "results": [
        {
            "title": "Logic Apps HTTP trigger",
            "url": "https://learn.microsoft.com/en-us/azure/logic-apps/http-trigger",
            "description": "Learn about HTTP triggers in Logic Apps.",
            "lastUpdatedDate": "2024-06-01",
        },
        {
            "title": "Service Bus connector",
            "url": "https://learn.microsoft.com/en-us/azure/logic-apps/service-bus",
            "description": "Use Service Bus with Logic Apps.",
        },
    ]
}


class TestMicrosoftLearnClient:
    """Tests for :class:`MicrosoftLearnClient`."""

    def test_search_happy_path(self) -> None:
        mock_resp = _make_httpx_response(json_body=_MS_LEARN_SEARCH_RESPONSE)

        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            ms_client = MicrosoftLearnClient(max_results=3)
            response = ms_client.search("HTTP trigger")

        assert response.provider == "microsoft_learn"
        assert response.query == "HTTP trigger"
        assert len(response.results) == 2
        assert response.results[0].title == "Logic Apps HTTP trigger"
        assert response.results[0].source == "microsoft_learn"
        assert response.results[0].metadata.get("last_updated") == "2024-06-01"
        assert response.results[1].metadata == {}
        assert response.duration_ms > 0
        assert response.error is None

    def test_search_empty_results(self) -> None:
        mock_resp = _make_httpx_response(json_body={"results": []})

        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            ms_client = MicrosoftLearnClient()
            response = ms_client.search("nonexistent topic")

        assert response.results == []
        assert response.error is None

    def test_search_timeout_raises(self) -> None:
        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.side_effect = httpx.ReadTimeout("timed out")

            ms_client = MicrosoftLearnClient(timeout=1.0)
            with pytest.raises(GroundingTimeoutError, match="timed out"):
                ms_client.search("query")

    def test_search_connect_error_raises(self) -> None:
        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.side_effect = httpx.ConnectError("connection refused")

            ms_client = MicrosoftLearnClient()
            with pytest.raises(GroundingConnectionError, match="Failed to connect"):
                ms_client.search("query")

    def test_search_http_status_error_raises(self) -> None:
        resp_500 = _make_httpx_response(status_code=500, json_body={"error": "server error"})

        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = resp_500

            ms_client = MicrosoftLearnClient()
            with pytest.raises(GroundingError, match="HTTP 500"):
                ms_client.search("query")

    def test_fetch_page_happy_path(self) -> None:
        mock_resp = _make_httpx_response(text_body="<html><body>Page content</body></html>")

        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            ms_client = MicrosoftLearnClient()
            response = ms_client.fetch_page("https://learn.microsoft.com/en-us/azure/logic-apps/overview")

        assert len(response.results) == 1
        assert "Page content" in response.results[0].content
        assert response.provider == "microsoft_learn"

    def test_fetch_page_timeout_raises(self) -> None:
        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.side_effect = httpx.ReadTimeout("timed out")

            ms_client = MicrosoftLearnClient()
            with pytest.raises(GroundingTimeoutError):
                ms_client.fetch_page("https://learn.microsoft.com/page")

    def test_custom_timeout_and_max_results(self) -> None:
        ms_client = MicrosoftLearnClient(timeout=5.0, max_results=10)
        assert ms_client._timeout == 5.0
        assert ms_client._max_results == 10


# ===================================================================
# Context7Client tests
# ===================================================================


_CONTEXT7_LIB_SEARCH_RESPONSE: dict[str, Any] = {
    "results": [
        {
            "id": "/mulesoft/docs-connectors",
            "title": "MuleSoft Connectors",
            "description": "MuleSoft connector documentation",
            "codeSnippets": 150,
            "sourceReputation": "High",
        },
    ]
}


class TestContext7Client:
    """Tests for :class:`Context7Client`."""

    def test_search_libraries_happy_path(self) -> None:
        mock_resp = _make_httpx_response(json_body=_CONTEXT7_LIB_SEARCH_RESPONSE)

        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            c7_client = Context7Client()
            response = c7_client.search_libraries("mulesoft connectors")

        assert response.provider == "context7"
        assert len(response.results) == 1
        assert response.results[0].title == "MuleSoft Connectors"
        assert response.results[0].metadata["library_id"] == "/mulesoft/docs-connectors"
        assert response.results[0].url == "https://context7.com/mulesoft/docs-connectors"
        assert response.error is None

    def test_search_libraries_empty(self) -> None:
        mock_resp = _make_httpx_response(json_body={"results": []})

        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            c7_client = Context7Client()
            response = c7_client.search_libraries("nonexistent")

        assert response.results == []

    def test_get_documentation_happy_path(self) -> None:
        doc_text = "# HTTP Listener\nConfigures an HTTP listener for Mule flows."
        mock_resp = _make_httpx_response(text_body=doc_text)

        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            c7_client = Context7Client(max_tokens=3000)
            response = c7_client.get_documentation("HTTP listener")

        assert response.provider == "context7"
        assert len(response.results) == 1
        assert response.results[0].content == doc_text
        assert response.results[0].metadata["library_id"] == "/mulesoft/docs-connectors"
        assert response.results[0].metadata["tokens_requested"] == 3000
        assert response.warnings == []

    def test_get_documentation_custom_library(self) -> None:
        mock_resp = _make_httpx_response(text_body="DataWeave content")

        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            c7_client = Context7Client()
            response = c7_client.get_documentation("map function", library_id="/mulesoft/docs-dataweave")

        assert response.results[0].metadata["library_id"] == "/mulesoft/docs-dataweave"

    def test_get_documentation_empty_response_warns(self) -> None:
        mock_resp = _make_httpx_response(text_body="")

        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            c7_client = Context7Client()
            response = c7_client.get_documentation("obscure topic")

        assert len(response.warnings) == 1
        assert "Empty response" in response.warnings[0]

    def test_search_libraries_timeout_raises(self) -> None:
        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.side_effect = httpx.ReadTimeout("timed out")

            c7_client = Context7Client(timeout=2.0)
            with pytest.raises(GroundingTimeoutError, match="timed out"):
                c7_client.search_libraries("query")

    def test_get_documentation_connect_error_raises(self) -> None:
        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.side_effect = httpx.ConnectError("refused")

            c7_client = Context7Client()
            with pytest.raises(GroundingConnectionError, match="Failed to connect"):
                c7_client.get_documentation("query")

    def test_get_documentation_http_error_raises(self) -> None:
        resp_429 = _make_httpx_response(status_code=429, text_body="rate limited")

        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = resp_429

            c7_client = Context7Client()
            with pytest.raises(GroundingError, match="HTTP 429"):
                c7_client.get_documentation("query")

    def test_mulesoft_libraries_mapping(self) -> None:
        assert "connectors" in Context7Client.MULESOFT_LIBRARIES
        assert "dataweave" in Context7Client.MULESOFT_LIBRARIES
        assert "general" in Context7Client.MULESOFT_LIBRARIES
        assert "api-manager" in Context7Client.MULESOFT_LIBRARIES
        assert "mule-sdk" in Context7Client.MULESOFT_LIBRARIES


# ===================================================================
# Tool function tests
# ===================================================================


class TestSearchLogicAppsDocs:
    """Tests for :func:`search_logic_apps_docs`."""

    def test_returns_json_on_success(self) -> None:
        mock_resp = _make_httpx_response(json_body=_MS_LEARN_SEARCH_RESPONSE)

        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            result_json = search_logic_apps_docs("HTTP trigger")

        data = json.loads(result_json)
        assert data["provider"] == "microsoft_learn"
        assert len(data["results"]) == 2
        assert data["error"] is None

    def test_prepends_logic_apps_to_query(self) -> None:
        mock_resp = _make_httpx_response(json_body={"results": []})

        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            search_logic_apps_docs("triggers")

            call_args = client_instance.get.call_args
            _, kwargs = call_args
            params = kwargs.get("params", {})
            assert "Azure Logic Apps Standard" in params["search"]

    def test_returns_error_json_on_failure(self) -> None:
        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.side_effect = httpx.ConnectError("no network")

            result_json = search_logic_apps_docs("query")

        data = json.loads(result_json)
        assert data["error"] == "Search failed"
        assert data["results"] == []
        assert data["provider"] == "microsoft_learn"


class TestFetchLogicAppsDoc:
    """Tests for :func:`fetch_logic_apps_doc`."""

    def test_returns_json_on_success(self) -> None:
        mock_resp = _make_httpx_response(text_body="<html>Content</html>")

        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            result_json = fetch_logic_apps_doc("https://learn.microsoft.com/page")

        data = json.loads(result_json)
        assert len(data["results"]) == 1
        assert "Content" in data["results"][0]["content"]

    def test_returns_error_json_on_failure(self) -> None:
        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.side_effect = httpx.ReadTimeout("timeout")

            result_json = fetch_logic_apps_doc("https://learn.microsoft.com/page")

        data = json.loads(result_json)
        assert data["error"] == "Fetch failed"


class TestSearchMulesoftDocs:
    """Tests for :func:`search_mulesoft_docs`."""

    def test_returns_json_on_success(self) -> None:
        mock_resp = _make_httpx_response(text_body="# HTTP Listener docs")

        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            result_json = search_mulesoft_docs("HTTP listener")

        data = json.loads(result_json)
        assert data["provider"] == "context7"
        assert len(data["results"]) == 1
        assert data["error"] is None

    def test_uses_specified_library(self) -> None:
        mock_resp = _make_httpx_response(text_body="DataWeave docs")

        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            result_json = search_mulesoft_docs("map function", library="dataweave")

        data = json.loads(result_json)
        assert data["results"][0]["metadata"]["library_id"] == "/mulesoft/docs-dataweave"

    def test_defaults_to_connectors_library(self) -> None:
        mock_resp = _make_httpx_response(text_body="connector docs")

        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            result_json = search_mulesoft_docs("HTTP listener")

        data = json.loads(result_json)
        assert data["results"][0]["metadata"]["library_id"] == "/mulesoft/docs-connectors"

    def test_returns_error_json_on_failure(self) -> None:
        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.side_effect = httpx.ConnectError("no network")

            result_json = search_mulesoft_docs("query")

        data = json.loads(result_json)
        assert data["error"] == "Search failed"
        assert data["results"] == []

    def test_unknown_library_falls_back_to_none(self) -> None:
        """When an unknown library key is passed, library_id will be None and the client defaults to connectors."""
        mock_resp = _make_httpx_response(text_body="fallback docs")

        with patch("m2la_agents.grounding.context7.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp

            result_json = search_mulesoft_docs("query", library="unknown")

        data = json.loads(result_json)
        # Should still succeed — the client defaults to connectors when None
        assert data["results"][0]["metadata"]["library_id"] == "/mulesoft/docs-connectors"


class TestResetClients:
    """Tests for the :func:`_reset_clients` helper."""

    def test_reset_clears_singletons(self) -> None:
        from m2la_agents.grounding import tool_functions

        # Force creation
        mock_resp = _make_httpx_response(json_body={"results": []})
        with patch("m2la_agents.grounding.microsoft_learn.httpx.Client") as mock_cls:
            client_instance = mock_cls.return_value.__enter__.return_value
            client_instance.get.return_value = mock_resp
            search_logic_apps_docs("test")

        assert tool_functions._ms_learn_client is not None

        _reset_clients()

        assert tool_functions._ms_learn_client is None
        assert tool_functions._context7_client is None
