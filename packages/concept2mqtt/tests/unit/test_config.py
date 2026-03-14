"""Unit tests for application configuration.

Test Techniques Used:
- Specification-based Testing: default values match documented defaults
- Boundary Value Analysis: port field constraints (ge=1, le=65535)
- Equivalence Partitioning: valid and invalid log_level variants
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

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


class TestPortBoundaryValues:
    """BVA: port field enforces ge=1, le=65535."""

    def test_port_min(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT", "1")
        assert Settings().port == 1

    def test_port_max(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT", "65535")
        assert Settings().port == 65535

    def test_port_below_min_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT", "0")
        with pytest.raises(ValidationError):
            Settings()

    def test_port_above_max_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT", "65536")
        with pytest.raises(ValidationError):
            Settings()


class TestLogLevelPartitions:
    """EP: log_level accepts all valid Literal variants; rejects others."""

    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    def test_valid_log_levels(
        self, monkeypatch: pytest.MonkeyPatch, level: str
    ) -> None:
        monkeypatch.setenv("LOG_LEVEL", level)
        assert Settings().log_level == level

    def test_invalid_log_level_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "VERBOSE")
        with pytest.raises(ValidationError):
            Settings()


class TestGetSettings:
    """get_settings() returns a cached Settings instance."""

    def test_returns_settings_instance(self, _reset_settings_cache: None) -> None:
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_is_cached(self, _reset_settings_cache: None) -> None:
        assert get_settings() is get_settings()
