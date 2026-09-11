"""FakePm5Adapter — test double implementing Pm5Port with canned responses.

This is a real, in-memory implementation of :class:`Pm5Port`, not a mock.
Tests assert against observable state (emitted events, connection status)
rather than call bookkeeping.

Usage with cosalette::

    from cosalette.testing import AppHarness
    from concept2mqtt.pm5.fake import FakePm5Adapter
    from concept2mqtt.pm5.port import Pm5Port

    harness = AppHarness.create(name="test")
    # Register via cosalette's adapter DI
    app = App("test", adapters={Pm5Port: lambda: FakePm5Adapter()})

Or use directly in unit tests::

    adapter = FakePm5Adapter()
    await adapter.connect()
    ident = await adapter.identity()
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from concept2mqtt.pm5.errors import Pm5ConnectionError
from concept2mqtt.pm5.types import (
    Pm5Event,
    Pm5Identity,
    Pm5Status,
    Pm5StatusEvent,
    RowingState,
    WorkoutState,
)

_DEFAULT_IDENTITY = Pm5Identity(
    serial_number="530426599",
    model="PM5",
    hardware_revision="672",
    firmware_revision="2.10",
    manufacturer="Concept2",
    erg_type="RowErg",
)

_IDLE_STATUS = Pm5Status(
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


@dataclass
class FakePm5Adapter:
    """In-memory PM5 test double implementing the Pm5Port Protocol.

    Args:
        identity_data: Canned identity returned by :meth:`identity`.
        events_to_emit: Events that :meth:`events` yields after connection,
            in order. The stream remains open for :meth:`emit` calls until
            :meth:`emit_done` or :meth:`disconnect` is called.
        connect_error: When set, :meth:`connect` raises it, simulating
            an unreachable PM5.
    """

    identity_data: Pm5Identity = field(default_factory=lambda: _DEFAULT_IDENTITY)
    events_to_emit: list[Pm5Event] = field(default_factory=list)
    connect_error: Exception | None = None

    connected: bool = field(default=False, init=False)
    connect_count: int = field(default=0, init=False)
    disconnect_count: int = field(default=0, init=False)
    _event_queue: asyncio.Queue[Pm5Event | None] = field(
        default_factory=asyncio.Queue, init=False
    )

    async def connect(self) -> None:
        if self.connect_error is not None:
            raise self.connect_error
        self.connected = True
        self.connect_count += 1
        # Enqueue pre-configured events
        for event in self.events_to_emit:
            self._event_queue.put_nowait(event)

    async def disconnect(self) -> None:
        self.connected = False
        self.disconnect_count += 1
        self.emit_done()

    async def identity(self) -> Pm5Identity:
        if not self.connected:
            raise Pm5ConnectionError("not connected")
        return self.identity_data

    async def events(self) -> AsyncIterator[Pm5Event]:
        """Yield events until :meth:`emit_done` or disconnect.

        Call :meth:`emit` to inject additional events dynamically.
        """
        while True:
            event = await self._event_queue.get()
            if event is None:
                return
            yield event

    def emit(self, event: Pm5Event) -> None:
        """Inject an event into the stream from outside.

        Useful in integration tests that need to simulate PM5 behaviour
        after the device handler has started consuming :meth:`events`.
        """
        self._event_queue.put_nowait(event)

    def emit_done(self) -> None:
        """Signal that no more events will follow."""
        self._event_queue.put_nowait(None)

    @staticmethod
    def idle_status_event() -> Pm5StatusEvent:
        """Convenience: a single idle status event."""
        return Pm5StatusEvent(status=_IDLE_STATUS)
