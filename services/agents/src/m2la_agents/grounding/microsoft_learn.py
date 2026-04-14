"""HTTP client for Microsoft Learn documentation search."""

from __future__ import annotations

import time
from typing import Any

import httpx

from m2la_agents.grounding.errors import GroundingConnectionError, GroundingError, GroundingTimeoutError
from m2la_agents.grounding.models import GroundingResponse, GroundingResult

_PROVIDER = "microsoft_learn"


class MicrosoftLearnClient:
    """HTTP client for Microsoft Learn documentation search.

    Uses the public Microsoft Learn search API to find documentation
    pages relevant to a given query.  No authentication is required.
    """

    BASE_URL = "https://learn.microsoft.com"
    DEFAULT_TIMEOUT = 15.0
    DEFAULT_MAX_RESULTS = 5

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> None:
        self._timeout = timeout
        self._max_results = max_results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str) -> GroundingResponse:
        """Search Microsoft Learn for documentation matching *query*.

        Args:
            query: Free-text search query.

        Returns:
            A :class:`GroundingResponse` with matching documentation results.

        Raises:
            GroundingTimeoutError: If the request times out.
            GroundingConnectionError: If a connection cannot be established.
            GroundingError: For any other HTTP transport error.
        """
        start = time.monotonic()
        params: dict[str, str | int] = {
            "search": query,
            "locale": "en-us",
            "$top": self._max_results,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(f"{self.BASE_URL}/api/search", params=params)
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise GroundingTimeoutError(
                f"Microsoft Learn search timed out after {self._timeout}s for query: {query!r}"
            ) from exc
        except httpx.ConnectError as exc:
            raise GroundingConnectionError(
                f"Failed to connect to Microsoft Learn for query: {query!r}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise GroundingError(
                f"Microsoft Learn returned HTTP {exc.response.status_code} for query: {query!r}"
            ) from exc
        except httpx.HTTPError as exc:
            raise GroundingError(
                f"Microsoft Learn request failed for query: {query!r}: {exc}"
            ) from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        data: dict[str, Any] = resp.json()
        results = _parse_search_results(data)

        return GroundingResponse(
            query=query,
            provider=_PROVIDER,
            results=results,
            duration_ms=round(elapsed_ms, 2),
        )

    def fetch_page(self, url: str) -> GroundingResponse:
        """Fetch a Microsoft Learn page and return its text content.

        Args:
            url: Full URL of a Microsoft Learn page.

        Returns:
            A single-result :class:`GroundingResponse` containing the page text.

        Raises:
            GroundingTimeoutError: If the request times out.
            GroundingConnectionError: If a connection cannot be established.
            GroundingError: For any other HTTP transport error.
        """
        start = time.monotonic()

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(url, headers={"Accept": "text/html"})
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise GroundingTimeoutError(
                f"Microsoft Learn page fetch timed out after {self._timeout}s for url: {url}"
            ) from exc
        except httpx.ConnectError as exc:
            raise GroundingConnectionError(
                f"Failed to connect to Microsoft Learn for url: {url}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise GroundingError(
                f"Microsoft Learn returned HTTP {exc.response.status_code} for url: {url}"
            ) from exc
        except httpx.HTTPError as exc:
            raise GroundingError(
                f"Microsoft Learn page fetch failed for url: {url}: {exc}"
            ) from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        content = resp.text

        result = GroundingResult(
            title=url,
            url=url,
            content=content,
            source=_PROVIDER,
        )

        return GroundingResponse(
            query=url,
            provider=_PROVIDER,
            results=[result],
            duration_ms=round(elapsed_ms, 2),
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _parse_search_results(data: dict[str, Any]) -> list[GroundingResult]:
    """Extract :class:`GroundingResult` objects from the raw API response."""
    results: list[GroundingResult] = []
    for item in data.get("results", []):
        title = item.get("title", "")
        url = item.get("url", "")
        description = item.get("description", "")
        last_updated = item.get("lastUpdatedDate", "")

        metadata: dict[str, Any] = {}
        if last_updated:
            metadata["last_updated"] = last_updated

        results.append(
            GroundingResult(
                title=title,
                url=url,
                content=description,
                source=_PROVIDER,
                metadata=metadata,
            )
        )
    return results
