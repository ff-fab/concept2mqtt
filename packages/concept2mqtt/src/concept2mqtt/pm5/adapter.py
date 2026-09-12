"""BleakPm5Adapter -- real BLE adapter implementing Pm5Port.

Uses `bleak <https://bleak.readthedocs.io/>`_ for BLE transport and the Rust
``csafe_codec`` for notification decoding and CSAFE framing.  This is the
production adapter that talks to actual PM5 hardware; for tests use
:class:`~concept2mqtt.pm5.fake.FakePm5Adapter`.

The adapter speaks exclusively in domain types at its public boundary (ADR-004).
Wire-format translation (centiseconds to seconds, decimetres to metres, etc.)
happens inside the adapter and never leaks through ``Pm5Port``.

Lifecycle::

    adapter = BleakPm5Adapter()
    await adapter.connect()      # scan + BLE connect + identity prefetch
    ident = await adapter.identity()
    async for event in adapter.events():
        ...
    await adapter.disconnect()
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

import csafe_codec
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from concept2mqtt.ble.profile import pm5_uuid
from concept2mqtt.pm5.errors import Pm5ConnectionError, Pm5TimeoutError
from concept2mqtt.pm5.types import (
    Pm5Event,
    Pm5ForceCurve,
    Pm5ForceCurveEvent,
    Pm5Identity,
    Pm5SplitInterval,
    Pm5SplitIntervalEvent,
    Pm5Status,
    Pm5StatusEvent,
    Pm5Stroke,
    Pm5StrokeEvent,
    Pm5WorkoutSummary,
    Pm5WorkoutSummaryEvent,
    RowingState,
    WorkoutState,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PM5_NAME_PREFIX = "PM5"
"""BLE local name prefix the PM5 advertises."""

DEFAULT_SCAN_TIMEOUT: float = 15.0
DEFAULT_RECONNECT_MIN: float = 2.0
DEFAULT_RECONNECT_MAX: float = 60.0
DEFAULT_CSAFE_TIMEOUT: float = 5.0
CSAFE_INTER_FRAME_GAP: float = 0.05
"""50 ms gap between CSAFE frames per Concept2 spec."""

# GATT characteristic UUID suffixes (expanded via pm5_uuid)
_CHAR_MODEL: str = pm5_uuid(0x0011)
_CHAR_SERIAL: str = pm5_uuid(0x0012)
_CHAR_HW_REV: str = pm5_uuid(0x0013)
_CHAR_FW_REV: str = pm5_uuid(0x0014)
_CHAR_MANUFACTURER: str = pm5_uuid(0x0015)
_CHAR_ERG_TYPE: str = pm5_uuid(0x0016)
_CHAR_PM_RX: str = pm5_uuid(0x0021)
_CHAR_PM_TX: str = pm5_uuid(0x0022)
_CHAR_SAMPLE_RATE: str = pm5_uuid(0x0034)

# Notification characteristic UUIDs mapped to their csafe_codec decoders.
_NotifyDecoder = Callable[[bytes], Any]

_NOTIFY_DECODERS: dict[str, tuple[str, _NotifyDecoder]] = {
    pm5_uuid(0x0031): ("general_status", csafe_codec.decode_general_status),
    pm5_uuid(0x0032): ("additional_status_1", csafe_codec.decode_additional_status_1),
    pm5_uuid(0x0033): ("additional_status_2", csafe_codec.decode_additional_status_2),
    pm5_uuid(0x0035): ("stroke_data", csafe_codec.decode_stroke_data),
    pm5_uuid(0x0036): (
        "additional_stroke_data",
        csafe_codec.decode_additional_stroke_data,
    ),
    pm5_uuid(0x0037): (
        "split_interval_data",
        csafe_codec.decode_split_interval_data,
    ),
    pm5_uuid(0x0038): (
        "additional_split_interval_data",
        csafe_codec.decode_additional_split_interval_data,
    ),
    pm5_uuid(0x0039): (
        "end_of_workout_summary",
        csafe_codec.decode_end_of_workout_summary,
    ),
    pm5_uuid(0x003A): (
        "end_of_workout_additional_summary",
        csafe_codec.decode_end_of_workout_additional_summary,
    ),
    pm5_uuid(0x003E): ("additional_status_3", csafe_codec.decode_additional_status_3),
}

# UUIDs that stream notifications (all NOTIFY chars from the rowing service).
_STREAMING_UUIDS: tuple[str, ...] = tuple(_NOTIFY_DECODERS)

# Erg machine type byte -> human-readable name.
_ERG_TYPE_NAMES: dict[int, str] = {
    0: "StaticD",
    1: "RowErg",
    2: "SkiErg",
    3: "BikeErg",
    4: "Dynamic",
    5: "Slides",
}


# ---------------------------------------------------------------------------
# Wire-to-domain mappers
# ---------------------------------------------------------------------------


def _workout_state(code: int) -> WorkoutState:
    """Map csafe_codec workout_state int to the domain enum."""
    mapping = {
        0: WorkoutState.IDLE,
        1: WorkoutState.IDLE,
        2: WorkoutState.STARTING,
        3: WorkoutState.STARTING,
        4: WorkoutState.STARTING,
        5: WorkoutState.ACTIVE,
        6: WorkoutState.ACTIVE,
        7: WorkoutState.PAUSED,
        8: WorkoutState.PAUSED,
        9: WorkoutState.PAUSED,
        10: WorkoutState.FINISHED,
        11: WorkoutState.FINISHED,
        12: WorkoutState.FINISHED,
        13: WorkoutState.FINISHED,
    }
    return mapping.get(code, WorkoutState.UNKNOWN)


def _rowing_state(code: int) -> RowingState:
    """Map csafe_codec rowing_state int to the domain enum."""
    mapping = {
        0: RowingState.INACTIVE,
        1: RowingState.DRIVE,
        2: RowingState.RECOVERY,
    }
    return mapping.get(code, RowingState.UNKNOWN)


def _map_general_status(
    gs: csafe_codec.GeneralStatus,
    as1: csafe_codec.AdditionalStatus1 | None,
    as2: csafe_codec.AdditionalStatus2 | None,
) -> Pm5Status:
    """Fuse GeneralStatus + AdditionalStatus1/2 into a single Pm5Status."""
    return Pm5Status(
        elapsed_time=gs.elapsed_time_cs / 100.0,
        distance=gs.distance_dm / 10.0,
        pace=as1.current_pace_cs / 100.0 if as1 else 0.0,
        speed=as1.speed_mms / 1000.0 if as1 else 0.0,
        stroke_rate=as1.stroke_rate if as1 else 0,
        heart_rate=as1.heartrate if as1 else 0,
        calories=as2.total_calories if as2 else 0,
        power=as2.average_power if as2 else 0,
        drag_factor=gs.drag_factor,
        workout_state=_workout_state(gs.workout_state),
        rowing_state=_rowing_state(gs.rowing_state),
    )


def _map_stroke(
    sd: csafe_codec.StrokeData,
    asd: csafe_codec.AdditionalStrokeData | None,
) -> Pm5Stroke:
    """Map StrokeData + AdditionalStrokeData to domain Pm5Stroke."""
    return Pm5Stroke(
        stroke_count=sd.stroke_count,
        drive_time=sd.drive_time / 100.0,
        recovery_time=sd.stroke_recovery_time_cs / 100.0,
        drive_length=sd.drive_length / 100.0,
        stroke_distance=sd.stroke_distance / 10.0,
        peak_force=sd.peak_drive_force / 10.0,
        average_force=sd.average_drive_force / 10.0,
        work_per_stroke=sd.work_per_stroke / 10.0,
        stroke_power=asd.stroke_power if asd else 0,
        stroke_calories=asd.stroke_calories / 1000.0 if asd else 0.0,
    )


def _map_workout_summary(s: csafe_codec.EndOfWorkoutSummary) -> Pm5WorkoutSummary:
    """Map EndOfWorkoutSummary to domain Pm5WorkoutSummary."""
    return Pm5WorkoutSummary(
        elapsed_time=s.elapsed_time_cs / 100.0,
        distance=s.distance_dm / 10.0,
        avg_pace=s.avg_pace_ds / 10.0,
        avg_stroke_rate=s.avg_stroke_rate,
        avg_heart_rate=s.avg_heartrate,
        avg_drag_factor=s.avg_drag_factor,
        workout_type=csafe_codec.workout_type_name(s.workout_type),
    )


def _map_split_interval(s: csafe_codec.SplitIntervalData) -> Pm5SplitInterval:
    """Map SplitIntervalData to domain Pm5SplitInterval."""
    return Pm5SplitInterval(
        number=s.split_interval_number,
        elapsed_time=s.elapsed_time_cs / 100.0,
        distance=s.distance_dm / 10.0,
        interval_type=csafe_codec.interval_type_name(s.split_interval_type),
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@dataclass
class BleakPm5Adapter:
    """Real BLE adapter implementing Pm5Port via bleak.

    Args:
        scan_timeout: Seconds to scan for a PM5 before giving up.
        reconnect_min: Initial reconnection backoff in seconds.
        reconnect_max: Maximum reconnection backoff in seconds.
        adapter: BLE adapter name (e.g. ``"hci0"``), or ``None`` for default.
        address: Connect to a specific BLE address instead of scanning.
    """

    scan_timeout: float = DEFAULT_SCAN_TIMEOUT
    reconnect_min: float = DEFAULT_RECONNECT_MIN
    reconnect_max: float = DEFAULT_RECONNECT_MAX
    adapter: str | None = None
    address: str | None = None

    _client: BleakClient | None = field(default=None, init=False, repr=False)
    _identity: Pm5Identity | None = field(default=None, init=False, repr=False)
    _event_queue: asyncio.Queue[Pm5Event | None] = field(
        default_factory=asyncio.Queue, init=False, repr=False
    )
    _connected: bool = field(default=False, init=False, repr=False)
    _subscribed_uuids: list[str] = field(default_factory=list, init=False, repr=False)

    # Cached latest decoded wire-format objects for status fusion.
    _latest_gs: csafe_codec.GeneralStatus | None = field(
        default=None, init=False, repr=False
    )
    _latest_as1: csafe_codec.AdditionalStatus1 | None = field(
        default=None, init=False, repr=False
    )
    _latest_as2: csafe_codec.AdditionalStatus2 | None = field(
        default=None, init=False, repr=False
    )
    _latest_sd: csafe_codec.StrokeData | None = field(
        default=None, init=False, repr=False
    )
    _latest_asd: csafe_codec.AdditionalStrokeData | None = field(
        default=None, init=False, repr=False
    )

    # CSAFE response tracking.
    _csafe_response: asyncio.Event = field(
        default_factory=asyncio.Event, init=False, repr=False
    )
    _csafe_response_data: bytes = field(default=b"", init=False, repr=False)
    _last_csafe_send: float = field(default=0.0, init=False, repr=False)

    # -----------------------------------------------------------------------
    # Pm5Port interface
    # -----------------------------------------------------------------------

    async def connect(self) -> None:
        """Scan for and connect to a PM5 over BLE.

        Raises:
            Pm5ConnectionError: If no PM5 is found or the connection fails.
        """
        device = await self._scan()
        await self._connect_device(device)
        self._identity = await self._read_identity()
        await self._subscribe_notifications()
        self._connected = True
        log.info(
            "Connected to PM5: serial=%s fw=%s",
            self._identity.serial_number,
            self._identity.firmware_revision,
        )

    async def disconnect(self) -> None:
        """Gracefully release the PM5 connection."""
        self._connected = False
        self._event_queue.put_nowait(None)
        await self._unsubscribe_notifications()
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except Exception:
                log.warning("Error during PM5 disconnect", exc_info=True)
        self._client = None
        log.info("Disconnected from PM5")

    async def identity(self) -> Pm5Identity:
        """Return the PM5's static device identity.

        Raises:
            Pm5ConnectionError: If not connected.
        """
        if not self._connected or self._identity is None:
            raise Pm5ConnectionError("not connected")
        return self._identity

    async def events(self) -> AsyncIterator[Pm5Event]:
        """Yield domain events decoded from PM5 BLE notifications.

        The iterator ends when the connection is closed or lost.
        """
        while self._connected:
            event = await self._event_queue.get()
            if event is None:
                return
            yield event

    # -----------------------------------------------------------------------
    # CSAFE command/response (c2m-bm7.4)
    # -----------------------------------------------------------------------

    async def send_csafe(self, command_bytes: bytes) -> bytes:
        """Send a CSAFE command frame and wait for the response.

        Enforces the 50 ms inter-frame gap required by the PM5.

        Args:
            command_bytes: A fully framed CSAFE command (from
                ``csafe_codec.build_command_frame`` or similar).

        Returns:
            The raw response bytes from the PM5 transmit characteristic.

        Raises:
            Pm5ConnectionError: If not connected.
            Pm5TimeoutError: If the PM5 does not respond within the timeout.
        """
        if not self._connected or self._client is None:
            raise Pm5ConnectionError("not connected")

        # Enforce inter-frame gap.
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_csafe_send
        if elapsed < CSAFE_INTER_FRAME_GAP:
            await asyncio.sleep(CSAFE_INTER_FRAME_GAP - elapsed)

        self._csafe_response.clear()
        self._csafe_response_data = b""

        try:
            await self._client.write_gatt_char(
                _CHAR_PM_RX, command_bytes, response=True
            )
        except Exception as exc:
            raise Pm5ConnectionError(f"CSAFE write failed: {exc}") from exc

        self._last_csafe_send = asyncio.get_event_loop().time()

        try:
            await asyncio.wait_for(
                self._csafe_response.wait(), timeout=DEFAULT_CSAFE_TIMEOUT
            )
        except TimeoutError as exc:
            raise Pm5TimeoutError("CSAFE response timeout") from exc

        return self._csafe_response_data

    # -----------------------------------------------------------------------
    # Notification rate (c2m-bm7.5)
    # -----------------------------------------------------------------------

    async def set_notification_rate(self, rate_byte: int) -> int:
        """Configure the PM5's notification sample rate.

        Writes a single byte to char ``0x0034``. The PM5 declares this
        characteristic as 1 byte; the official app writes 8 bytes which
        the PM5 rejects (hardware finding 2026-09-06). This method writes
        exactly 1 byte.

        Args:
            rate_byte: The sample rate value (0-255).

        Returns:
            The rate value read back from the PM5 after writing.

        Raises:
            Pm5ConnectionError: If not connected.
        """
        if not self._connected or self._client is None:
            raise Pm5ConnectionError("not connected")

        payload = bytes([rate_byte & 0xFF])
        try:
            await self._client.write_gatt_char(
                _CHAR_SAMPLE_RATE, payload, response=True
            )
        except Exception as exc:
            raise Pm5ConnectionError(f"notification rate write failed: {exc}") from exc

        # Read back to verify the rate took effect.
        try:
            data = await self._client.read_gatt_char(_CHAR_SAMPLE_RATE)
            return data[0] if data else rate_byte
        except Exception:
            log.warning("Could not read back notification rate", exc_info=True)
            return rate_byte

    # -----------------------------------------------------------------------
    # Internal: scanning and connection
    # -----------------------------------------------------------------------

    async def _scan(self) -> BLEDevice:
        """Scan for a PM5 by name prefix.

        Returns:
            The discovered BLE device.

        Raises:
            Pm5ConnectionError: If no PM5 is found within the scan timeout.
        """
        if self.address is not None:
            device = await BleakScanner.find_device_by_address(
                self.address,
                timeout=self.scan_timeout,
                adapter=self.adapter or "hci0",
            )
        else:
            device = await BleakScanner.find_device_by_filter(
                lambda d, _adv: bool(d.name and PM5_NAME_PREFIX in d.name),
                timeout=self.scan_timeout,
                adapter=self.adapter or "hci0",
            )

        if device is None:
            raise Pm5ConnectionError(f"No PM5 found within {self.scan_timeout}s scan")
        log.info("Found PM5: %s (%s)", device.name, device.address)
        return device

    async def _connect_device(self, device: BLEDevice) -> None:
        """Establish the BLE connection to the discovered device."""
        self._client = BleakClient(
            device,
            disconnected_callback=self._on_disconnect,
        )
        try:
            await self._client.connect()
        except Exception as exc:
            self._client = None
            raise Pm5ConnectionError(f"BLE connect failed: {exc}") from exc

    def _on_disconnect(self, _client: BleakClient) -> None:
        """Handle unexpected BLE disconnection."""
        log.warning("PM5 BLE connection lost")
        self._connected = False
        self._event_queue.put_nowait(None)

    # -----------------------------------------------------------------------
    # Internal: identity
    # -----------------------------------------------------------------------

    async def _read_identity(self) -> Pm5Identity:
        """Read PM5 identity characteristics from the GATT server."""
        client = self._client
        if client is None:
            raise Pm5ConnectionError("not connected")

        async def _read_str(uuid: str) -> str:
            data = await client.read_gatt_char(uuid)
            return bytes(data).decode("utf-8").strip("\x00")

        async def _read_byte(uuid: str) -> int:
            data = await client.read_gatt_char(uuid)
            return data[0] if data else 0

        try:
            (
                model,
                serial,
                hw_rev,
                fw_rev,
                manufacturer,
                erg_type_byte,
            ) = await asyncio.gather(
                _read_str(_CHAR_MODEL),
                _read_str(_CHAR_SERIAL),
                _read_str(_CHAR_HW_REV),
                _read_str(_CHAR_FW_REV),
                _read_str(_CHAR_MANUFACTURER),
                _read_byte(_CHAR_ERG_TYPE),
            )
        except Exception as exc:
            raise Pm5ConnectionError(f"Failed to read PM5 identity: {exc}") from exc

        return Pm5Identity(
            serial_number=serial,
            model=model,
            hardware_revision=hw_rev,
            firmware_revision=fw_rev,
            manufacturer=manufacturer,
            erg_type=_ERG_TYPE_NAMES.get(erg_type_byte, f"unknown({erg_type_byte})"),
        )

    # -----------------------------------------------------------------------
    # Internal: notifications
    # -----------------------------------------------------------------------

    async def _subscribe_notifications(self) -> None:
        """Subscribe to all streaming characteristics on the PM5."""
        if self._client is None:
            raise Pm5ConnectionError("not connected")

        for uuid in _STREAMING_UUIDS:
            try:
                await self._client.start_notify(uuid, self._on_notification)
                self._subscribed_uuids.append(uuid)
            except Exception:
                log.warning("PM5 does not stream %s; skipping", uuid, exc_info=True)

        # Also subscribe to the CSAFE transmit characteristic for responses.
        try:
            await self._client.start_notify(_CHAR_PM_TX, self._on_csafe_response)
        except Exception:
            log.warning(
                "Could not subscribe to CSAFE transmit characteristic",
                exc_info=True,
            )

        log.info(
            "Subscribed to %d/%d streaming characteristics",
            len(self._subscribed_uuids),
            len(_STREAMING_UUIDS),
        )

    async def _unsubscribe_notifications(self) -> None:
        """Unsubscribe from all notification characteristics."""
        if self._client is None or not self._client.is_connected:
            return
        for uuid in self._subscribed_uuids:
            with contextlib.suppress(Exception):
                await self._client.stop_notify(uuid)
        with contextlib.suppress(Exception):
            await self._client.stop_notify(_CHAR_PM_TX)
        self._subscribed_uuids.clear()

    def _on_notification(self, _sender: Any, data: bytearray) -> None:
        """Decode a BLE notification and enqueue the resulting domain event.

        Called from bleak's callback context.  The sender is the
        characteristic handle; we need the UUID, which bleak passes as
        the sender for characteristic objects.
        """
        uuid: str = str(_sender).lower() if not isinstance(_sender, int) else ""
        # bleak >= 0.21 passes BleakGATTCharacteristic as sender
        if hasattr(_sender, "uuid"):
            uuid = str(_sender.uuid).lower()

        raw = bytes(data)
        entry = _NOTIFY_DECODERS.get(uuid)
        if entry is None:
            return

        name, decoder = entry
        try:
            decoded = decoder(raw)
        except Exception:
            log.debug("Failed to decode %s notification", name, exc_info=True)
            return

        event = self._to_domain_event(name, decoded)
        if event is not None:
            self._event_queue.put_nowait(event)

    def _on_csafe_response(self, _sender: Any, data: bytearray) -> None:
        """Handle a CSAFE response notification on the PM Transmit char."""
        self._csafe_response_data = bytes(data)
        self._csafe_response.set()

    def _to_domain_event(self, name: str, decoded: Any) -> Pm5Event | None:
        """Map a decoded notification to a domain event, fusing multi-char data."""
        handler = self._EVENT_HANDLERS.get(name)
        if handler is None:
            log.debug("Received %s notification (not mapped)", name)
            return None
        return handler(self, decoded)

    def _handle_general_status(self, decoded: Any) -> Pm5Event:
        self._latest_gs = decoded
        return self._fused_status_event()

    def _handle_additional_status_1(self, decoded: Any) -> Pm5Event | None:
        self._latest_as1 = decoded
        return self._fused_status_event() if self._latest_gs else None

    def _handle_additional_status_2(self, decoded: Any) -> Pm5Event | None:
        self._latest_as2 = decoded
        return self._fused_status_event() if self._latest_gs else None

    def _handle_stroke_data(self, decoded: Any) -> Pm5Event:
        self._latest_sd = decoded
        return Pm5StrokeEvent(stroke=_map_stroke(self._latest_sd, self._latest_asd))

    def _handle_additional_stroke_data(self, decoded: Any) -> Pm5Event | None:
        self._latest_asd = decoded
        if self._latest_sd is None:
            return None
        return Pm5StrokeEvent(stroke=_map_stroke(self._latest_sd, self._latest_asd))

    def _handle_workout_summary(self, decoded: Any) -> Pm5Event:  # noqa: ARG001
        return Pm5WorkoutSummaryEvent(summary=_map_workout_summary(decoded))

    def _handle_split_interval(self, decoded: Any) -> Pm5Event:  # noqa: ARG001
        return Pm5SplitIntervalEvent(split=_map_split_interval(decoded))

    def _handle_force_curve(self, decoded: Any) -> Pm5Event:  # noqa: ARG001
        return Pm5ForceCurveEvent(
            force_curve=Pm5ForceCurve(data_points=decoded.data_points)
        )

    def _fused_status_event(self) -> Pm5StatusEvent:
        """Build a Pm5StatusEvent from the latest cached wire-format data."""
        return Pm5StatusEvent(
            status=_map_general_status(
                self._latest_gs, self._latest_as1, self._latest_as2
            )
        )

    _EVENT_HANDLERS: ClassVar[dict[str, Callable[..., Pm5Event | None]]] = {
        "general_status": _handle_general_status,
        "additional_status_1": _handle_additional_status_1,
        "additional_status_2": _handle_additional_status_2,
        "stroke_data": _handle_stroke_data,
        "additional_stroke_data": _handle_additional_stroke_data,
        "end_of_workout_summary": _handle_workout_summary,
        "split_interval_data": _handle_split_interval,
        "force_curve_data": _handle_force_curve,
    }
