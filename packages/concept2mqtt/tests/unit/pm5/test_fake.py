"""Unit tests for concept2mqtt/pm5/fake.py — FakePm5Adapter test double.

Test Techniques Used:
- Specification-based Testing: Protocol conformance, constructor contracts
- State Transition Testing: connected/disconnected lifecycle
- Error Guessing: identity before connect, connect failure injection
"""

from __future__ import annotations

import pytest

from concept2mqtt.pm5.errors import Pm5ConnectionError
from concept2mqtt.pm5.fake import FakePm5Adapter
from concept2mqtt.pm5.port import Pm5Port
from concept2mqtt.pm5.types import (
    Pm5Identity,
    Pm5Status,
    Pm5StatusEvent,
    Pm5Stroke,
    Pm5StrokeEvent,
    RowingState,
    WorkoutState,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def adapter() -> FakePm5Adapter:
    """Default adapter with no pre-configured events."""
    return FakePm5Adapter()


@pytest.fixture
def status_event() -> Pm5StatusEvent:
    """A mid-workout status event."""
    return Pm5StatusEvent(
        status=Pm5Status(
            elapsed_time=60.0,
            distance=250.0,
            pace=120.0,
            speed=2.08,
            stroke_rate=28,
            heart_rate=155,
            calories=10,
            power=180,
            drag_factor=120,
            workout_state=WorkoutState.ACTIVE,
            rowing_state=RowingState.DRIVE,
        )
    )


@pytest.fixture
def stroke_event() -> Pm5StrokeEvent:
    """A stroke event."""
    return Pm5StrokeEvent(
        stroke=Pm5Stroke(
            stroke_count=10,
            drive_time=0.85,
            recovery_time=1.15,
            drive_length=1.35,
            stroke_distance=9.8,
            peak_force=450.0,
            average_force=320.0,
            work_per_stroke=285.0,
            stroke_power=190,
            stroke_calories=3.5,
        )
    )


# =============================================================================
# Protocol conformance
# =============================================================================


class TestProtocolConformance:
    """FakePm5Adapter satisfies the Pm5Port Protocol.

    Technique: Specification-based Testing — structural subtyping.
    """

    def test_adapter_is_pm5port(self, adapter: FakePm5Adapter) -> None:
        """isinstance check against the @runtime_checkable Pm5Port."""
        assert isinstance(adapter, Pm5Port)


# =============================================================================
# Connection lifecycle
# =============================================================================


class TestConnectionLifecycle:
    """Connect/disconnect state transitions.

    Technique: State Transition Testing — disconnected -> connected -> disconnected.
    """

    async def test_connect_sets_connected(self, adapter: FakePm5Adapter) -> None:
        assert not adapter.connected

        await adapter.connect()

        assert adapter.connected
        assert adapter.connect_count == 1

    async def test_disconnect_clears_connected(self, adapter: FakePm5Adapter) -> None:
        await adapter.connect()

        await adapter.disconnect()

        assert not adapter.connected
        assert adapter.disconnect_count == 1

    async def test_connect_increments_count(self, adapter: FakePm5Adapter) -> None:
        """Multiple connects are counted (simulates reconnection)."""
        await adapter.connect()
        await adapter.disconnect()
        await adapter.connect()

        assert adapter.connect_count == 2

    async def test_connect_error_injection(self) -> None:
        """When connect_error is set, connect() raises it.

        Technique: Error Guessing — simulating unreachable PM5.
        """
        adapter = FakePm5Adapter(connect_error=Pm5ConnectionError("PM5 not found"))

        with pytest.raises(Pm5ConnectionError, match="PM5 not found"):
            await adapter.connect()

        assert not adapter.connected


# =============================================================================
# Identity
# =============================================================================


class TestIdentity:
    """identity() returns the canned identity data.

    Technique: Specification-based Testing.
    """

    async def test_identity_returns_default(self, adapter: FakePm5Adapter) -> None:
        await adapter.connect()

        ident = await adapter.identity()

        assert ident.serial_number == "530426599"
        assert ident.model == "PM5"

    async def test_identity_returns_custom(self) -> None:
        custom = Pm5Identity("999", "PM5+", "1", "3.0", "Concept2", "BikeErg")
        adapter = FakePm5Adapter(identity_data=custom)
        await adapter.connect()

        ident = await adapter.identity()

        assert ident.serial_number == "999"
        assert ident.erg_type == "BikeErg"

    async def test_identity_raises_when_not_connected(
        self, adapter: FakePm5Adapter
    ) -> None:
        """Technique: Error Guessing — calling identity() before connect()."""
        with pytest.raises(Pm5ConnectionError, match="not connected"):
            await adapter.identity()


# =============================================================================
# Event stream
# =============================================================================


class TestEventStream:
    """events() yields pre-configured events, then stops.

    Technique: Specification-based Testing — event delivery contract.
    """

    async def test_empty_events_stream(self, adapter: FakePm5Adapter) -> None:
        """No pre-configured events yields nothing."""
        await adapter.connect()

        events = [e async for e in adapter.events()]

        assert events == []

    async def test_preconfigured_events(
        self, status_event: Pm5StatusEvent, stroke_event: Pm5StrokeEvent
    ) -> None:
        """Pre-configured events are yielded in order."""
        adapter = FakePm5Adapter(events_to_emit=[status_event, stroke_event])
        await adapter.connect()

        events = [e async for e in adapter.events()]

        assert len(events) == 2
        assert isinstance(events[0], Pm5StatusEvent)
        assert isinstance(events[1], Pm5StrokeEvent)

    async def test_emit_injects_event_dynamically(
        self, adapter: FakePm5Adapter, status_event: Pm5StatusEvent
    ) -> None:
        """emit() adds an event to the stream from outside."""
        await adapter.connect()
        # Drain the initial stream (empty)
        _ = [e async for e in adapter.events()]

        # Inject a new event and consume it
        adapter.emit(status_event)
        adapter.emit_done()

        events = [e async for e in adapter.events()]
        assert len(events) == 1
        assert events[0] is status_event

    async def test_idle_status_event_factory(self) -> None:
        """Convenience factory returns an idle status event."""
        event = FakePm5Adapter.idle_status_event()

        assert isinstance(event, Pm5StatusEvent)
        assert event.status.workout_state is WorkoutState.IDLE
        assert event.status.rowing_state is RowingState.INACTIVE
        assert event.status.elapsed_time == 0.0
