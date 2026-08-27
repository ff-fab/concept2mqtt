"""Byte-level BLE relay between the real PM5 and an emulated PM5 peripheral.

The PM5 accepts only one simultaneous BLE connection (ADR-003), so
concept2mqtt holds it and re-serves it. :class:`BleRelay` is the transport-free
core of that re-serving: it wires a :class:`CentralLink` (the real PM5, on the
central-side adapter) to a :class:`PeripheralServer` (the emulated PM5, on a
second adapter) and moves opaque bytes between them.

The relay deliberately does not decode CSAFE. Decoding belongs to the MQTT
publishing path, which taps the same notification stream via ``tap``.

Peripheral-side reads and writes are logged at ``DEBUG``. Because the Pi is
itself the GATT server the app connects to, that log is the record of which
UUIDs a connecting app touched — no external BLE sniffer needed. See
``docs/testing/pm5-ble-relay-hardware-validation.md``.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from concept2mqtt.ble.errors import CharacteristicAccessError
from concept2mqtt.ble.profile import GattProfile

log = logging.getLogger(__name__)

#: Called with ``(characteristic_uuid, payload)`` for each inbound notification.
NotifyCallback = Callable[[str, bytes], Awaitable[None]]


class CentralLink(Protocol):
    """The central-side connection to the real PM5."""

    async def read(self, uuid: str) -> bytes:
        """Read a characteristic value from the PM5."""
        ...

    async def write(self, uuid: str, data: bytes, *, response: bool) -> None:
        """Write a characteristic value to the PM5."""
        ...

    async def start_notify(self, uuid: str, callback: NotifyCallback) -> None:
        """Subscribe to a PM5 characteristic's notifications."""
        ...

    async def stop_notify(self, uuid: str) -> None:
        """Unsubscribe from a PM5 characteristic's notifications."""
        ...


class PeripheralServer(Protocol):
    """The peripheral-side GATT server impersonating the PM5."""

    async def start(
        self,
        profile: GattProfile,
        *,
        on_read: Callable[[str], Awaitable[bytes]],
        on_write: Callable[[str, bytes], Awaitable[None]],
    ) -> None:
        """Register the profile's services and begin advertising."""
        ...

    async def stop(self) -> None:
        """Stop advertising and unregister the services."""
        ...

    async def notify(self, uuid: str, data: bytes) -> None:
        """Push a notification to the connected consumer."""
        ...


@dataclass(slots=True)
class RelayStats:
    """Counters describing relay throughput, for hardware validation runs."""

    notifications_relayed: int = 0
    writes_relayed: int = 0
    reads_served: int = 0
    notify_errors: int = 0
    unavailable_characteristics: int = 0


class BleRelay:
    """Relay PM5 traffic between a central link and an emulated peripheral.

    Args:
        central: Connection to the real PM5.
        peripheral: GATT server impersonating the PM5.
        profile: Profile both sides speak; also the allow-list of UUIDs.
        tap: Optional observer receiving every relayed notification, so the
            MQTT publishing path can consume the same stream.

    Example:
        ```python
        relay = BleRelay(central=link, peripheral=server, profile=get_profile())
        await relay.start()
        ```
    """

    def __init__(
        self,
        *,
        central: CentralLink,
        peripheral: PeripheralServer,
        profile: GattProfile,
        tap: NotifyCallback | None = None,
    ) -> None:
        self._central = central
        self._peripheral = peripheral
        self._profile = profile
        self._tap = tap
        self._cache: dict[str, bytes] = {}
        self._streaming = tuple(c.uuid for c in profile if c.streaming)
        self._subscribed: list[str] = []
        self.stats = RelayStats()

    @property
    def subscribed(self) -> tuple[str, ...]:
        """UUIDs currently subscribed to on the PM5."""
        return tuple(self._subscribed)

    async def start(self) -> None:
        """Subscribe to PM5 notifications, then start advertising as a PM5.

        Characteristics the connected PM5 firmware does not implement are
        skipped with a warning: the spec marks several as firmware-dependent,
        and one missing stream must not cost the app every other one.
        """
        for uuid in self._streaming:
            try:
                await self._central.start_notify(uuid, self._on_notification)
            except Exception:
                self.stats.unavailable_characteristics += 1
                log.warning("PM5 does not stream %s; skipping", uuid, exc_info=True)
            else:
                self._subscribed.append(uuid)
        await self._peripheral.start(
            self._profile, on_read=self._on_read, on_write=self._on_write
        )
        log.info(
            "BLE relay started: profile=%s services=%d streaming=%d/%d",
            self._profile.name,
            len(self._profile.services),
            len(self._subscribed),
            len(self._streaming),
        )

    async def stop(self) -> None:
        """Stop advertising and unsubscribe from PM5 notifications."""
        await self._peripheral.stop()
        while self._subscribed:
            await self._central.stop_notify(self._subscribed.pop())
        log.info("BLE relay stopped: %s", self.stats)

    async def _on_notification(self, uuid: str, data: bytes) -> None:
        """Forward a PM5 notification to the emulated peripheral and the tap.

        Delivery failures are counted and logged rather than raised: a consumer
        that has disconnected or stalled must not tear down the sole PM5 link.
        """
        payload = bytes(data)
        try:
            await self._peripheral.notify(uuid, payload)
        except Exception:
            self.stats.notify_errors += 1
            log.warning("Dropped notification for %s", uuid, exc_info=True)
        else:
            self.stats.notifications_relayed += 1
        if self._tap is not None:
            await self._tap(uuid, payload)

    async def _on_read(self, uuid: str) -> bytes:
        """Serve a peripheral-side read, reading through to the PM5 once.

        Raises:
            UnknownCharacteristicError: UUID is not in the profile.
            CharacteristicAccessError: Characteristic is not readable.
        """
        characteristic = self._profile.characteristic(uuid)
        log.debug("Consumer read %s (%s)", characteristic.uuid, characteristic.name)
        if not characteristic.readable:
            raise CharacteristicAccessError(uuid, "read")
        if characteristic.uuid not in self._cache:
            self._cache[characteristic.uuid] = await self._central.read(
                characteristic.uuid
            )
        self.stats.reads_served += 1
        return self._cache[characteristic.uuid]

    async def _on_write(self, uuid: str, data: bytes) -> None:
        """Forward a peripheral-side write to the PM5.

        Raises:
            UnknownCharacteristicError: UUID is not in the profile.
            CharacteristicAccessError: Characteristic is not writable.
        """
        characteristic = self._profile.characteristic(uuid)
        log.debug(
            "Consumer write %s (%s): %d bytes",
            characteristic.uuid,
            characteristic.name,
            len(data),
        )
        if not characteristic.writable:
            raise CharacteristicAccessError(uuid, "write")
        payload = bytes(data)
        await self._central.write(
            characteristic.uuid,
            payload,
            response=characteristic.write_with_response,
        )
        if characteristic.readable:
            self._cache[characteristic.uuid] = payload
        self.stats.writes_relayed += 1
