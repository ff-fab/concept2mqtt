"""Pm5Port — hexagonal port defining the domain-level PM5 interface.

Adapters (``BleakPm5Adapter``, ``FakePm5Adapter``) implement this Protocol.
Device handlers obtain an adapter via cosalette's DI::

    pm5 = ctx.adapter(Pm5Port)

The port speaks exclusively in domain types (:mod:`concept2mqtt.pm5.types`),
never in BLE bytes, GATT UUIDs, or CSAFE wire format.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from concept2mqtt.pm5.types import Pm5Event, Pm5Identity


@runtime_checkable
class Pm5Port(Protocol):
    """Domain-level interface to a Concept2 PM5 rowing monitor.

    Implementations manage their own connection lifecycle. The port
    consumer (a cosalette device handler) calls :meth:`connect` at
    startup, iterates :meth:`events` for the duration of the session,
    and calls :meth:`disconnect` at shutdown.
    """

    async def connect(self) -> None:
        """Establish a connection to the PM5.

        Raises:
            Pm5ConnectionError: If the PM5 cannot be reached.
        """
        ...

    async def disconnect(self) -> None:
        """Gracefully release the PM5 connection."""
        ...

    async def identity(self) -> Pm5Identity:
        """Read the PM5's static device identity.

        Must be called after :meth:`connect`. The result is stable for
        the lifetime of a connection.

        Raises:
            Pm5ConnectionError: If the connection has been lost.
        """
        ...

    def events(self) -> AsyncIterator[Pm5Event]:
        """Stream of domain events from the PM5.

        Yields decoded, SI-unit events as they arrive from the monitor.
        The iterator ends when the connection is closed or lost.
        """
        ...
