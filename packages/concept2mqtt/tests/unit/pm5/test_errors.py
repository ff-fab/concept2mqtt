"""Unit tests for concept2mqtt/pm5/errors.py — PM5 domain exceptions.

Test Techniques Used:
- Specification-based Testing: exception hierarchy, constructor contracts
- Error Guessing: catch-by-base-class behaviour
"""

from __future__ import annotations

import pytest

from concept2mqtt.pm5.errors import (
    Pm5CommandError,
    Pm5ConnectionError,
    Pm5Error,
    Pm5TimeoutError,
)

# =============================================================================
# Hierarchy
# =============================================================================


class TestExceptionHierarchy:
    """All PM5 exceptions inherit from Pm5Error.

    Technique: Specification-based Testing — hierarchy contract.
    """

    @pytest.mark.parametrize(
        "exc_class",
        [Pm5ConnectionError, Pm5CommandError, Pm5TimeoutError],
        ids=["connection", "command", "timeout"],
    )
    def test_subclass_of_pm5_error(self, exc_class: type[Pm5Error]) -> None:
        """Every PM5 exception is catchable via ``except Pm5Error``."""
        assert issubclass(exc_class, Pm5Error)

    @pytest.mark.parametrize(
        "exc_class",
        [Pm5ConnectionError, Pm5CommandError, Pm5TimeoutError],
        ids=["connection", "command", "timeout"],
    )
    def test_subclass_of_exception(self, exc_class: type[Pm5Error]) -> None:
        """PM5 exceptions are standard Python exceptions."""
        assert issubclass(exc_class, Exception)


# =============================================================================
# Pm5CommandError
# =============================================================================


class TestPm5CommandError:
    """Pm5CommandError carries the failed command name and reason.

    Technique: Specification-based Testing — constructor and field access.
    """

    def test_command_error_fields(self) -> None:
        err = Pm5CommandError(command="GET_STATUS", reason="timeout waiting for reply")
        assert err.command == "GET_STATUS"
        assert err.reason == "timeout waiting for reply"

    def test_command_error_message(self) -> None:
        err = Pm5CommandError(command="SET_PROGRAM", reason="rejected")
        assert "SET_PROGRAM" in str(err)
        assert "rejected" in str(err)

    def test_command_error_catchable_as_pm5_error(self) -> None:
        """Technique: Error Guessing — catch-by-base-class."""
        with pytest.raises(Pm5Error):
            raise Pm5CommandError(command="RESET", reason="not idle")


# =============================================================================
# Pm5ConnectionError
# =============================================================================


class TestPm5ConnectionError:
    """Pm5ConnectionError has no extra fields — it's a simple signal.

    Technique: Specification-based Testing.
    """

    def test_connection_error_message(self) -> None:
        err = Pm5ConnectionError("PM5 not found")
        assert str(err) == "PM5 not found"


# =============================================================================
# Pm5TimeoutError
# =============================================================================


class TestPm5TimeoutError:
    """Pm5TimeoutError signals an operation that took too long.

    Technique: Specification-based Testing.
    """

    def test_timeout_error_message(self) -> None:
        err = Pm5TimeoutError("identity read timed out after 5s")
        assert "5s" in str(err)
