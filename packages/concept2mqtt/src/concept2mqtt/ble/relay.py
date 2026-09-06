"""Byte-level BLE relay between the real PM5 and an emulated PM5 peripheral.

The PM5 accepts only one simultaneous BLE connection (ADR-003), so
concept2mqtt holds it and re-serves it. :class:`BleRelay` is the transport-free
core of that re-serving: it wires a :class:`CentralLink` (the real PM5, on the
central-side adapter) to a :class:`PeripheralServer` (the emulated PM5, on a
second adapter) and moves opaque bytes between them.

The relay deliberately does not decode CSAFE. Decoding belongs to the MQTT
publishing path, which taps the same notification stream via ``tap``.

Because the Pi is itself the GATT server the app connects to, the relay's log
is the record of which UUIDs a connecting app touched — no external BLE
sniffer needed. Reads and writes are logged at ``DEBUG``; subscriptions, which
decide what actually goes on the air, at ``INFO``. See
``docs/testing/pm5-ble-relay-hardware-validation.md``.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter
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

    def is_subscribed(self, uuid: str) -> bool:
        """Whether the connected consumer has enabled ``uuid``'s CCCD."""
        ...


@dataclass(slots=True)
class RelayStats:
    """Counters describing relay throughput, for hardware validation runs.

    ``notifications_withheld`` and the two ``forward_seconds`` fields exist to
    attribute end-to-end latency: the 2026-09-05 run could tell that the relay
    added ~1 s over a direct connection but not where it went, because a
    forward that the peripheral silently discarded (consumer not subscribed)
    counted the same as one that reached the air.
    """

    notifications_relayed: int = 0
    notifications_withheld: int = 0
    writes_relayed: int = 0
    write_errors: int = 0
    reads_served: int = 0
    notify_errors: int = 0
    unavailable_characteristics: int = 0
    reconnects: int = 0
    forward_seconds_total: float = 0.0
    forward_seconds_max: float = 0.0

    @property
    def _forward_attempts(self) -> int:
        """Notifications handed to the peripheral, whether or not it accepted them.

        ``forward_seconds_total``/``_max`` accumulate for every attempt in
        :meth:`BleRelay._on_notification`, a failed one (``notify_errors``)
        included — the timing covers the call regardless of its outcome.
        """
        return self.notifications_relayed + self.notify_errors

    @property
    def forward_ms_mean(self) -> float:
        """Mean time spent handing a notification to the peripheral, in ms."""
        attempts = self._forward_attempts
        if not attempts:
            return 0.0
        return 1000 * self.forward_seconds_total / attempts


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
        self._consumer_subscribed: set[str] = set()
        self.stats = RelayStats()

    @property
    def subscribed(self) -> tuple[str, ...]:
        """UUIDs currently subscribed to on the PM5."""
        return tuple(self._subscribed)

    @property
    def consumer_subscribed(self) -> frozenset[str]:
        """UUIDs the connected consumer has subscribed to via its CCCDs."""
        return frozenset(self._consumer_subscribed)

    async def start(self) -> None:
        """Start advertising as a PM5, then subscribe to PM5 notifications.

        The peripheral is registered first so that it can accept the very
        first notification: subscribing on the central beforehand made the
        PM5's opening burst arrive at a GATT server that did not exist yet,
        and the 2026-09-05 hardware run lost ~5 s of telemetry that way.

        Characteristics the connected PM5 firmware does not implement are
        skipped with a warning: the spec marks several as firmware-dependent,
        and one missing stream must not cost the app every other one.
        """
        await self._peripheral.start(
            self._profile, on_read=self._on_read, on_write=self._on_write
        )
        await self._subscribe_central()
        log.info(
            "BLE relay started: profile=%s services=%d streaming=%d/%d",
            self._profile.name,
            len(self._profile.services),
            len(self._subscribed),
            len(self._streaming),
        )

    async def rebind_central(self, central: CentralLink) -> None:
        """Resume relaying over a freshly reconnected PM5 link.

        The peripheral is deliberately untouched: the consumer keeps its
        connection and its subscriptions across a PM5 dropout, and simply sees
        a gap in the stream. Cached reads are kept too — they hold the erg's
        identity, which does not change when the link does.
        """
        self._central = central
        self.stats.reconnects += 1
        await self._subscribe_central()
        log.info(
            "BLE relay rebound to the PM5: streaming=%d/%d",
            len(self._subscribed),
            len(self._streaming),
        )

    async def _subscribe_central(self) -> None:
        """Subscribe to every streaming characteristic the firmware offers."""
        self._subscribed.clear()
        unavailable = 0
        for uuid in self._streaming:
            try:
                await self._central.start_notify(uuid, self._on_notification)
            except Exception:
                unavailable += 1
                log.warning("PM5 does not stream %s; skipping", uuid, exc_info=True)
            else:
                self._subscribed.append(uuid)
        # Assigned, not accumulated: this describes the firmware in front of
        # us, so a reconnect must not double-count the same missing stream.
        self.stats.unavailable_characteristics = unavailable

    async def stop(self) -> None:
        """Stop advertising and unsubscribe from PM5 notifications."""
        await self._peripheral.stop()
        while self._subscribed:
            await self._central.stop_notify(self._subscribed.pop())
        log.info("BLE relay stopped: %s", self.stats)

    def _consumer_wants(self, uuid: str) -> bool:
        """Whether to forward ``uuid``, logging every change of mind.

        Which characteristics the Concept2 app actually subscribes to was an
        open question after the 2026-09-05 run, so each transition is logged
        at INFO — the answer is then in any relay log, not just a DEBUG one.
        """
        subscribed = self._peripheral.is_subscribed(uuid)
        if subscribed != (uuid in self._consumer_subscribed):
            verb = "subscribed to" if subscribed else "unsubscribed from"
            log.info("Consumer %s %s", verb, uuid)
            if subscribed:
                self._consumer_subscribed.add(uuid)
            else:
                self._consumer_subscribed.discard(uuid)
        return subscribed

    async def _on_notification(self, uuid: str, data: bytes) -> None:
        """Forward a PM5 notification to the emulated peripheral and the tap.

        Only characteristics the consumer subscribed to are forwarded. The
        peripheral would discard the rest anyway, but silently, which made the
        relay counters overstate what actually reached the air.

        The tap always sees the notification: MQTT publishing does not depend
        on a consumer being connected.

        Delivery failures are counted and logged rather than raised: a consumer
        that has disconnected or stalled must not tear down the sole PM5 link.
        """
        payload = bytes(data)
        if self._consumer_wants(uuid):
            started = perf_counter()
            try:
                await self._peripheral.notify(uuid, payload)
            except Exception:
                self.stats.notify_errors += 1
                log.warning("Dropped notification for %s", uuid, exc_info=True)
            else:
                self.stats.notifications_relayed += 1
            elapsed = perf_counter() - started
            self.stats.forward_seconds_total += elapsed
            self.stats.forward_seconds_max = max(
                self.stats.forward_seconds_max, elapsed
            )
        else:
            self.stats.notifications_withheld += 1
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
        if len(payload) > characteristic.max_length:
            # The real PM5 declares this characteristic's length, so a phone
            # writing to the erg directly is constrained before the write goes
            # out. The emulated server does not enforce it, so the consumer's
            # full payload arrives here and the PM5 answers an ATT Invalid
            # Attribute Value Length — silently discarding it.
            #
            # Measured 2026-09-06: the Concept2 app writes 02 00 00 00 00 00
            # 00 00 to the 1-byte ce060034, i.e. a little-endian 64-bit 2,
            # meaning a 250 ms sample rate. Rejected, so the PM5 stayed at its
            # 1 Hz default and the app ran ~1 s behind. Clamping to the
            # declared length is what the real erg's own length contract would
            # have done (R-LATENCY-5).
            log.warning(
                "Consumer wrote %d bytes to %s (%s), which holds %d: %s"
                " — truncating to fit",
                len(payload),
                characteristic.uuid,
                characteristic.name,
                characteristic.max_length,
                payload.hex(" "),
            )
            payload = payload[: characteristic.max_length]
        try:
            await self._central.write(
                characteristic.uuid,
                payload,
                response=characteristic.write_with_response,
            )
        except Exception:
            # Counted and re-raised: the consumer must see the failure, and the
            # count is the evidence for whether a rejected write is what keeps
            # the PM5 at its slow default notification rate (R-LATENCY-5).
            self.stats.write_errors += 1
            log.warning(
                "PM5 rejected a %d-byte write to %s (%s)",
                len(payload),
                characteristic.uuid,
                characteristic.name,
                exc_info=True,
            )
            raise
        if characteristic.readable:
            self._cache[characteristic.uuid] = payload
        self.stats.writes_relayed += 1
