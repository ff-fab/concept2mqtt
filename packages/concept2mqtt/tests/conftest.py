"""Pytest configuration and shared fixtures."""

import pytest

from .fixtures.config import _reset_settings_cache as _reset_settings_cache


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (may require external services)"
    )
