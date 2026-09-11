"""Unit tests for concept2mqtt/pm5/port.py — Pm5Port Protocol conformance.

Test Techniques Used:
- Specification-based Testing: Protocol structural subtyping contract
- Error Guessing: incomplete implementations are not Protocol-compatible
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from concept2mqtt.pm5.port import Pm5Port
from concept2mqtt.pm5.types import (
    Pm5Event,
    Pm5Identity,
    Pm5Status,
    Pm5StatusEvent,
    RowingState,
    WorkoutState,
)

# =============================================================================
# Minimal conforming implementation (test-only)
# =============================================================================


class _MinimalPm5Adapter:
    """Bare-minimum implementation satisfying the Pm5Port Protocol."""

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def identity(self) -> Pm5Identity:
        return Pm5Identity("0", "PM5", "1", "1.0", "Concept2", "RowErg")

    async def events(self) -> AsyncIterator[Pm5Event]:
        yield Pm5StatusEvent(
            status=Pm5Status(
                elapsed_time=0.0,
                distance=0.0,
                pace=0.0,
                speed=0.0,
                stroke_rate=0,
                heart_rate=0,
                calories=0,
                power=0,
                drag_factor=0,
                workout_state=WorkoutState.IDLE,
                rowing_state=RowingState.INACTIVE,
            )
        )


# =============================================================================
# Tests
# =============================================================================


class TestPm5PortProtocol:
    """Pm5Port is a structural Protocol — implementations need not inherit it.

    Technique: Specification-based Testing — structural subtyping.
    """

    def test_minimal_adapter_satisfies_protocol(self) -> None:
        """A class with the right methods is accepted as Pm5Port.

        Pm5Port is @runtime_checkable, so isinstance checks structural
        compatibility without requiring inheritance.
        """
        adapter = _MinimalPm5Adapter()
        assert isinstance(adapter, Pm5Port)

    def test_port_defines_expected_methods(self) -> None:
        """Pm5Port exposes the four methods device handlers need."""
        expected = {"connect", "disconnect", "identity", "events"}
        # Get methods defined in the Protocol (not inherited from object)
        protocol_methods = {
            name
            for name in dir(Pm5Port)
            if not name.startswith("_") and callable(getattr(Pm5Port, name))
        }
        assert expected <= protocol_methods

    async def test_minimal_adapter_identity_returns_domain_type(self) -> None:
        """The identity() method returns a Pm5Identity, not raw bytes."""
        adapter = _MinimalPm5Adapter()
        ident = await adapter.identity()
        assert isinstance(ident, Pm5Identity)
        assert ident.serial_number == "0"

    async def test_minimal_adapter_events_yields_domain_events(self) -> None:
        """The events() method yields Pm5Event instances."""
        adapter = _MinimalPm5Adapter()
        events_seen: list[Pm5Event] = []
        async for event in adapter.events():
            events_seen.append(event)
        assert len(events_seen) == 1
        assert isinstance(events_seen[0], Pm5StatusEvent)
