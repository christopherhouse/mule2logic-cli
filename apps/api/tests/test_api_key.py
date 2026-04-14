"""Tests for POC API token authentication middleware.

This module covers the ``verify_api_key`` dependency used to protect all
endpoints except ``/health``.  The API token is set via the ``M2LA_API_TOKEN``
environment variable.

NOTE: This is POC auth – it will be replaced by Microsoft Entra ID.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from m2la_api.config.settings import get_settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Endpoints that require auth (any POST endpoint will do)
_PROTECTED_ENDPOINTS = [
    ("/analyze", {"input_path": "/tmp/project"}),
    ("/transform", {"input_path": "/tmp/project"}),
    ("/validate", {"output_directory": "/tmp/output"}),
]


def _fresh_app() -> FastAPI:
    """Import a **fresh** FastAPI app after env / cache changes.

    Because ``get_settings`` is cached with ``@lru_cache`` and the ``app``
    module-level object captures the dependency at import time, we must
    clear the cache *before* re-importing so that the new environment
    variables take effect.
    """
    import importlib
    import sys
    from pathlib import Path

    get_settings.cache_clear()

    # Also clear the chat client cache since it depends on settings
    from m2la_api.dependencies import get_chat_client

    get_chat_client.cache_clear()

    import m2la_api.main as main_mod

    importlib.reload(main_mod)

    # Override the chat client with MockChatClient so routes don't fail
    _agents_tests = str(Path(__file__).resolve().parents[3] / "services" / "agents" / "tests")
    if _agents_tests not in sys.path:
        sys.path.insert(0, _agents_tests)
    from mock_chat_client import MockChatClient

    main_mod.app.dependency_overrides[get_chat_client] = lambda: MockChatClient()

    return main_mod.app


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestApiTokenAuth:
    """Tests for the x-api-token authentication dependency."""

    # -- No token configured (local-dev mode) --------------------------------

    @pytest.mark.asyncio
    async def test_no_token_configured_allows_health(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Health endpoint is accessible when no API token is configured."""
        monkeypatch.delenv("M2LA_API_TOKEN", raising=False)
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_no_token_configured_allows_protected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Protected endpoints are accessible when no API token is configured."""
        monkeypatch.delenv("M2LA_API_TOKEN", raising=False)
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path, body in _PROTECTED_ENDPOINTS:
                resp = await client.post(path, json=body)
                # Routes may return 503 (Foundry not configured) — that's OK.
                # The point is they don't return 401.
                assert resp.status_code != 401, f"{path} should not be 401 without token"

    # -- Token configured – valid requests -----------------------------------

    @pytest.mark.asyncio
    async def test_correct_token_allows_protected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Correct x-api-token header grants access to protected endpoints."""
        monkeypatch.setenv("M2LA_API_TOKEN", "my-secret")
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path, body in _PROTECTED_ENDPOINTS:
                resp = await client.post(path, json=body, headers={"x-api-token": "my-secret"})
                # Routes may return 503 (Foundry not configured) — that's OK.
                # The point is they don't return 401.
                assert resp.status_code != 401, f"{path} should not be 401 with correct token"

    # -- Token configured – missing header -----------------------------------

    @pytest.mark.asyncio
    async def test_missing_token_returns_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Requests without x-api-token header get 401 when auth is enabled."""
        monkeypatch.setenv("M2LA_API_TOKEN", "my-secret")
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path, body in _PROTECTED_ENDPOINTS:
                resp = await client.post(path, json=body)
                assert resp.status_code == 401, f"{path} should be 401 without header"

    # -- Token configured – wrong header value -------------------------------

    @pytest.mark.asyncio
    async def test_wrong_token_returns_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Requests with an incorrect x-api-token get 401."""
        monkeypatch.setenv("M2LA_API_TOKEN", "my-secret")
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path, body in _PROTECTED_ENDPOINTS:
                resp = await client.post(path, json=body, headers={"x-api-token": "wrong-key"})
                assert resp.status_code == 401, f"{path} should be 401 with wrong token"

    # -- Health always public ------------------------------------------------

    @pytest.mark.asyncio
    async def test_health_always_public_with_token_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Health endpoint is accessible even when API token auth is enabled."""
        monkeypatch.setenv("M2LA_API_TOKEN", "my-secret")
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_health_public_without_matching_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Health returns 200 even with wrong/missing token when auth enabled."""
        monkeypatch.setenv("M2LA_API_TOKEN", "my-secret")
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health", headers={"x-api-token": "totally-wrong"})
        assert resp.status_code == 200
