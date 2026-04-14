"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings driven by environment variables.

    All settings can be overridden via environment variables prefixed with ``M2LA_``.
    """

    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "info"
    debug: bool = False
    # POC API token auth – will be replaced by Entra ID authentication.
    api_token: str = ""
    # Azure AI Foundry connection settings.
    foundry_endpoint: str = ""
    foundry_model: str = "gpt-4o"
    # Azure Monitor connection string is read from
    # APPLICATIONINSIGHTS_CONNECTION_STRING (no M2LA_ prefix).

    model_config = {"env_prefix": "M2LA_"}


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()
