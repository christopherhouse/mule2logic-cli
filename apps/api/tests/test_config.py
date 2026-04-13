"""Tests for application configuration."""

import pytest

from m2la_api.config.settings import Settings, get_settings


class TestSettings:
    """Tests for the Settings model."""

    def test_defaults(self) -> None:
        """Settings should have sensible defaults."""
        settings = Settings()
        assert settings.host == "127.0.0.1"
        assert settings.port == 8000
        assert settings.log_level == "info"
        assert settings.debug is False

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables should override defaults."""
        monkeypatch.setenv("M2LA_HOST", "0.0.0.0")
        monkeypatch.setenv("M2LA_PORT", "9000")
        monkeypatch.setenv("M2LA_LOG_LEVEL", "debug")
        monkeypatch.setenv("M2LA_DEBUG", "true")
        settings = Settings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 9000
        assert settings.log_level == "debug"
        assert settings.debug is True

    def test_partial_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Only overridden env vars should change; others keep defaults."""
        monkeypatch.setenv("M2LA_PORT", "3000")
        settings = Settings()
        assert settings.port == 3000
        assert settings.host == "127.0.0.1"  # default


class TestGetSettings:
    """Tests for the get_settings() cached dependency."""

    def test_returns_settings_instance(self) -> None:
        # Clear the lru_cache to get fresh settings
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_cached(self) -> None:
        """Consecutive calls should return the same cached instance."""
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
