"""Tests for POC API key authentication middleware.

This module covers the ``verify_api_key`` dependency used to protect all
endpoints except ``/health``.  The API key is set via the ``M2LA_API_KEY``
environment variable.

NOTE: This is POC auth – it will be replaced by Microsoft Entra ID.
"""

import pytest
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


def _fresh_app() -> "FastAPI":  # noqa: F821
    """Import a **fresh** FastAPI app after env / cache changes.

    Because ``get_settings`` is cached with ``@lru_cache`` and the ``app``
    module-level object captures the dependency at import time, we must
    clear the cache *before* re-importing so that the new environment
    variables take effect.
    """
    import importlib

    get_settings.cache_clear()
    import m2la_api.main as main_mod

    importlib.reload(main_mod)
    return main_mod.app


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestApiKeyAuth:
    """Tests for the X-API-Key authentication dependency."""

    # -- No key configured (local-dev mode) ---------------------------------

    @pytest.mark.asyncio
    async def test_no_key_configured_allows_health(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Health endpoint is accessible when no API key is configured."""
        monkeypatch.delenv("M2LA_API_KEY", raising=False)
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_no_key_configured_allows_protected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Protected endpoints are accessible when no API key is configured."""
        monkeypatch.delenv("M2LA_API_KEY", raising=False)
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path, body in _PROTECTED_ENDPOINTS:
                resp = await client.post(path, json=body)
                assert resp.status_code == 200, f"{path} should be 200 without key"

    # -- Key configured – valid requests ------------------------------------

    @pytest.mark.asyncio
    async def test_correct_key_allows_protected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Correct X-API-Key header grants access to protected endpoints."""
        monkeypatch.setenv("M2LA_API_KEY", "my-secret")
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path, body in _PROTECTED_ENDPOINTS:
                resp = await client.post(path, json=body, headers={"X-API-Key": "my-secret"})
                assert resp.status_code == 200, f"{path} should be 200 with correct key"

    # -- Key configured – missing header ------------------------------------

    @pytest.mark.asyncio
    async def test_missing_key_returns_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Requests without X-API-Key header get 401 when auth is enabled."""
        monkeypatch.setenv("M2LA_API_KEY", "my-secret")
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path, body in _PROTECTED_ENDPOINTS:
                resp = await client.post(path, json=body)
                assert resp.status_code == 401, f"{path} should be 401 without header"

    # -- Key configured – wrong header value --------------------------------

    @pytest.mark.asyncio
    async def test_wrong_key_returns_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Requests with an incorrect X-API-Key get 401."""
        monkeypatch.setenv("M2LA_API_KEY", "my-secret")
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path, body in _PROTECTED_ENDPOINTS:
                resp = await client.post(path, json=body, headers={"X-API-Key": "wrong-key"})
                assert resp.status_code == 401, f"{path} should be 401 with wrong key"

    # -- Health always public -----------------------------------------------

    @pytest.mark.asyncio
    async def test_health_always_public_with_key_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Health endpoint is accessible even when API key auth is enabled."""
        monkeypatch.setenv("M2LA_API_KEY", "my-secret")
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_health_public_without_matching_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Health returns 200 even with wrong/missing key when auth enabled."""
        monkeypatch.setenv("M2LA_API_KEY", "my-secret")
        app = _fresh_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health", headers={"X-API-Key": "totally-wrong"})
        assert resp.status_code == 200
