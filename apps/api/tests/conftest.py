"""Shared test fixtures for API tests.

Provides a MockChatClient override so that route tests don't require
a real Foundry connection.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport

# Ensure the agents test infrastructure is importable
_AGENTS_TESTS_DIR = str(Path(__file__).resolve().parents[3] / "services" / "agents" / "tests")
if _AGENTS_TESTS_DIR not in sys.path:
    sys.path.insert(0, _AGENTS_TESTS_DIR)

from mock_chat_client import MockChatClient  # noqa: E402

from m2la_api.dependencies import get_chat_client  # noqa: E402
from m2la_api.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _override_chat_client() -> None:
    """Override the Foundry chat client with MockChatClient for all tests."""
    mock_client = MockChatClient()
    app.dependency_overrides[get_chat_client] = lambda: mock_client
    yield  # type: ignore[misc]
    app.dependency_overrides.pop(get_chat_client, None)


@pytest.fixture
def transport() -> ASGITransport:
    """Return an ASGI transport for the test app."""
    return ASGITransport(app=app)
