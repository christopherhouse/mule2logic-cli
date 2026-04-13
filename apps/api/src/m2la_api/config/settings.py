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

    model_config = {"env_prefix": "M2LA_"}


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()
