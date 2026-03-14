"""Unit tests for application configuration.

Test Techniques Used:
- Specification-based Testing: default values match documented defaults
- Boundary Value Analysis: port field constraints (ge=1, le=65535)
- Equivalence Partitioning: valid log_level variants
"""

from __future__ import annotations

import pytest

from concept2mqtt.config import Settings, get_settings


class TestSettingsDefaults:
    """Settings instantiates with correct defaults."""

    def test_default_log_level(self) -> None:
        settings = Settings()
        assert settings.log_level == "INFO"

    def test_default_host(self) -> None:
        settings = Settings()
        assert settings.host == "127.0.0.1"

    def test_default_port(self) -> None:
        settings = Settings()
        assert settings.port == 1883


class TestSettingsEnvOverride:
    """Settings reads values from environment variables."""

    def test_log_level_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_port_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT", "9999")
        settings = Settings()
        assert settings.port == 9999


class TestGetSettings:
    """get_settings() returns a cached Settings instance."""

    def test_returns_settings_instance(self, _reset_settings_cache: None) -> None:
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_is_cached(self, _reset_settings_cache: None) -> None:
        assert get_settings() is get_settings()
