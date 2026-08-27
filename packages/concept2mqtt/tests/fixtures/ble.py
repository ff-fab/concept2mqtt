"""Test doubles for the BLE relay's central and peripheral sides.

Both doubles are real, in-memory implementations of the relay's protocols
rather than mocks: assertions are made against observable state (recorded
writes, delivered notifications) instead of call bookkeeping.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from concept2mqtt.ble.profile import GattProfile
from concept2mqtt.ble.relay import NotifyCallback


@dataclass
class FakeCentralLink:
    """In-memory stand-in for the connection to the real PM5.

    Args:
        values: Characteristic values the fake PM5 will return on read.
        unavailable: UUIDs whose subscription fails, simulating a firmware
            version that does not implement that characteristic.
    """

    values: dict[str, bytes] = field(default_factory=dict)
    unavailable: set[str] = field(default_factory=set)
    writes: list[tuple[str, bytes, bool]] = field(default_factory=list)
    subscriptions: dict[str, NotifyCallback] = field(default_factory=dict)
    reads: list[str] = field(default_factory=list)

    async def read(self, uuid: str) -> bytes:
        self.reads.append(uuid)
        return self.values[uuid]

    async def write(self, uuid: str, data: bytes, *, response: bool) -> None:
        self.writes.append((uuid, data, response))

    async def start_notify(self, uuid: str, callback: NotifyCallback) -> None:
        if uuid in self.unavailable:
            raise RuntimeError(f"characteristic {uuid} not implemented by firmware")
        self.subscriptions[uuid] = callback

    async def stop_notify(self, uuid: str) -> None:
        self.subscriptions.pop(uuid, None)

    async def emit(self, uuid: str, data: bytes | bytearray) -> None:
        """Simulate the PM5 sending a notification on ``uuid``.

        Accepts ``bytearray`` because real BLE stacks deliver mutable buffers
        that they are free to reuse after the callback returns.
        """
        await self.subscriptions[uuid](uuid, bytes(data))


@dataclass
class FakePeripheralServer:
    """In-memory stand-in for the emulated PM5 GATT server.

    Args:
        notify_error: When set, every ``notify`` call raises it, simulating a
            consumer that has disconnected or a stalled D-Bus link.
    """

    notify_error: Exception | None = None
    profile: GattProfile | None = None
    running: bool = False
    notifications: list[tuple[str, bytes]] = field(default_factory=list)
    on_read: Callable[[str], Awaitable[bytes]] | None = None
    on_write: Callable[[str, bytes], Awaitable[None]] | None = None

    async def start(
        self,
        profile: GattProfile,
        *,
        on_read: Callable[[str], Awaitable[bytes]],
        on_write: Callable[[str, bytes], Awaitable[None]],
    ) -> None:
        self.profile = profile
        self.on_read = on_read
        self.on_write = on_write
        self.running = True

    async def stop(self) -> None:
        self.running = False

    async def notify(self, uuid: str, data: bytes) -> None:
        if self.notify_error is not None:
            raise self.notify_error
        self.notifications.append((uuid, data))

    async def read(self, uuid: str) -> bytes:
        """Simulate a connected consumer reading ``uuid``."""
        assert self.on_read is not None, "server not started"
        return await self.on_read(uuid)

    async def write(self, uuid: str, data: bytes) -> None:
        """Simulate a connected consumer writing ``uuid``."""
        assert self.on_write is not None, "server not started"
        await self.on_write(uuid, data)
