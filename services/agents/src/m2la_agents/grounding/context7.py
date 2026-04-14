"""HTTP client for the Context7 documentation service."""

from __future__ import annotations

import time
from typing import Any

import httpx

from m2la_agents.grounding.errors import GroundingConnectionError, GroundingError, GroundingTimeoutError
from m2la_agents.grounding.models import GroundingResponse, GroundingResult

_PROVIDER = "context7"


class Context7Client:
    """HTTP client for the Context7 documentation service.

    Context7 provides library-specific documentation context.  This
    client is pre-configured with MuleSoft library IDs so agents can
    quickly look up connector and runtime documentation.
    """

    BASE_URL = "https://context7.com/api/v2"
    DEFAULT_TIMEOUT = 15.0
    DEFAULT_MAX_TOKENS = 2000

    # Pre-configured library IDs for MuleSoft documentation.
    MULESOFT_LIBRARIES: dict[str, str] = {
        "connectors": "/mulesoft/docs-connectors",
        "dataweave": "/mulesoft/docs-dataweave",
        "general": "/mulesoft/docs-general",
        "api-manager": "/mulesoft/docs-api-manager",
        "mule-sdk": "/mulesoft/docs-mule-sdk",
    }

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._timeout = timeout
        self._max_tokens = max_tokens

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_libraries(self, query: str) -> GroundingResponse:
        """Search Context7 for libraries matching *query*.

        Args:
            query: Library name to search for.

        Returns:
            A :class:`GroundingResponse` with matching library entries.

        Raises:
            GroundingTimeoutError: If the request times out.
            GroundingConnectionError: If a connection cannot be established.
            GroundingError: For any other HTTP transport error.
        """
        start = time.monotonic()
        params: dict[str, str] = {"libraryName": query}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(f"{self.BASE_URL}/libs/search", params=params)
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise GroundingTimeoutError(
                f"Context7 library search timed out after {self._timeout}s for query: {query!r}"
            ) from exc
        except httpx.ConnectError as exc:
            raise GroundingConnectionError(
                f"Failed to connect to Context7 for query: {query!r}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise GroundingError(
                f"Context7 returned HTTP {exc.response.status_code} for query: {query!r}"
            ) from exc
        except httpx.HTTPError as exc:
            raise GroundingError(
                f"Context7 library search failed for query: {query!r}: {exc}"
            ) from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        data: dict[str, Any] = resp.json()
        results = _parse_library_results(data)

        return GroundingResponse(
            query=query,
            provider=_PROVIDER,
            results=results,
            duration_ms=round(elapsed_ms, 2),
        )

    def get_documentation(
        self,
        query: str,
        *,
        library_id: str | None = None,
    ) -> GroundingResponse:
        """Get documentation context for a MuleSoft topic.

        Args:
            query: Free-text query describing the documentation needed.
            library_id: Context7 library identifier.  Defaults to
                ``/mulesoft/docs-connectors`` when not specified.

        Returns:
            A :class:`GroundingResponse` wrapping the plain-text
            documentation content.

        Raises:
            GroundingTimeoutError: If the request times out.
            GroundingConnectionError: If a connection cannot be established.
            GroundingError: For any other HTTP transport error.
        """
        if library_id is None:
            library_id = self.MULESOFT_LIBRARIES["connectors"]

        start = time.monotonic()
        params: dict[str, str | int] = {
            "libraryId": library_id,
            "query": query,
            "tokens": self._max_tokens,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(f"{self.BASE_URL}/context", params=params)
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise GroundingTimeoutError(
                f"Context7 doc fetch timed out after {self._timeout}s for query: {query!r}"
            ) from exc
        except httpx.ConnectError as exc:
            raise GroundingConnectionError(
                f"Failed to connect to Context7 for query: {query!r}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise GroundingError(
                f"Context7 returned HTTP {exc.response.status_code} for query: {query!r}"
            ) from exc
        except httpx.HTTPError as exc:
            raise GroundingError(
                f"Context7 doc fetch failed for query: {query!r}: {exc}"
            ) from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        content = resp.text

        warnings: list[str] = []
        if not content.strip():
            warnings.append(f"Empty response from Context7 for library_id={library_id!r}, query={query!r}")

        result = GroundingResult(
            title=f"Context7: {library_id}",
            url=f"{self.BASE_URL}/context?libraryId={library_id}&query={query}",
            content=content,
            source=_PROVIDER,
            metadata={"library_id": library_id, "tokens_requested": self._max_tokens},
        )

        return GroundingResponse(
            query=query,
            provider=_PROVIDER,
            results=[result],
            duration_ms=round(elapsed_ms, 2),
            warnings=warnings,
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _parse_library_results(data: dict[str, Any]) -> list[GroundingResult]:
    """Extract :class:`GroundingResult` objects from a library search response."""
    results: list[GroundingResult] = []
    for item in data.get("results", []):
        lib_id = item.get("id", "")
        title = item.get("title", lib_id)

        metadata: dict[str, Any] = {"library_id": lib_id}
        for key in ("description", "codeSnippets", "sourceReputation", "benchmarkScore"):
            if key in item:
                metadata[key] = item[key]

        results.append(
            GroundingResult(
                title=title,
                url=f"https://context7.com{lib_id}" if lib_id.startswith("/") else "",
                content=item.get("description", ""),
                source=_PROVIDER,
                metadata=metadata,
            )
        )
    return results
