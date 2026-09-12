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
        extra="ignore",
        str_strip_whitespace=True,
    )

    # Application settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Network service settings
    host: str = "127.0.0.1"
    port: Annotated[int, Field(ge=1, le=65535)] = 1883

    # Production PM5 binding. At least one must be configured by main().
    pm5_address: Annotated[str | None, Field(min_length=1)] = None
    pm5_serial_number: Annotated[str | None, Field(min_length=1)] = None

    def pm5_adapter_kwargs(self) -> dict[str, str]:
        """Return trusted PM5 selection arguments for the production adapter.

        Raises:
            ValueError: If no PM5 address or serial number is configured.
        """
        if self.pm5_address is None and self.pm5_serial_number is None:
            msg = "Set PM5_ADDRESS and/or PM5_SERIAL_NUMBER before starting"
            raise ValueError(msg)

        kwargs: dict[str, str] = {}
        if self.pm5_address is not None:
            kwargs["address"] = self.pm5_address
        if self.pm5_serial_number is not None:
            kwargs["expected_serial_number"] = self.pm5_serial_number
        return kwargs


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
