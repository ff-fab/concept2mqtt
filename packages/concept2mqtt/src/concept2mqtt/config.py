"""Application configuration via pydantic-settings.

Configuration is loaded from environment variables and/or .env files.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Network service settings
    host: str = "127.0.0.1"
    port: Annotated[int, Field(ge=1, le=65535)] = 1883


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings instance (cached after first call).

    Note:
        Uses ``@lru_cache`` — call ``get_settings.cache_clear()`` in tests that
        mutate environment variables, or use the ``_reset_settings_cache``
        fixture from ``tests/fixtures/config.py``.
    """
    return Settings()
