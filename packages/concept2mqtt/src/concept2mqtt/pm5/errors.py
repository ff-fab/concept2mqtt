"""PM5 domain exceptions.

These exceptions represent domain-level failures that device handlers can
catch and react to. They are deliberately transport-agnostic: a
``Pm5ConnectionError`` means the PM5 is unreachable, regardless of whether
the underlying transport is BLE, USB, or a test double.
"""

from __future__ import annotations


class Pm5Error(Exception):
    """Base class for all PM5 domain errors."""


class Pm5ConnectionError(Pm5Error):
    """The PM5 is unreachable or the connection was lost."""


class Pm5CommandError(Pm5Error):
    """A CSAFE command was rejected or produced an unexpected response."""

    def __init__(self, command: str, reason: str) -> None:
        super().__init__(f"command {command!r} failed: {reason}")
        self.command = command
        self.reason = reason


class Pm5TimeoutError(Pm5Error):
    """An operation exceeded its time budget."""
