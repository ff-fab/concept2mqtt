"""Unit tests for concept2mqtt/pm5/adapter.py -- BleakPm5Adapter.

Tests cover all four beads tasks:
- c2m-bm7.1: BLE scanning and connection
- c2m-bm7.2: Device identity reading
- c2m-bm7.3: Notification subscription and event streaming
- c2m-bm7.4: CSAFE request/response
- c2m-bm7.5: Notification rate configuration

BLE I/O (bleak) is mocked at the transport boundary. Domain-level logic
(wire-to-domain mapping, notification fusion, reconnection) is tested
with real code paths.

Test Techniques Used:
- Specification-based Testing: Pm5Port Protocol conformance
- State Transition Testing: connected/disconnected lifecycle
- Equivalence Partitioning: valid/invalid notification payloads
- Boundary Value Analysis: scan timeout, reconnection delays, CSAFE timeout
- Error Guessing: scan failure, connect failure, disconnect during stream
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any, override
from unittest.mock import AsyncMock, patch

import csafe_codec
import pytest

from concept2mqtt.pm5.adapter import (
    BleakPm5Adapter,
    _map_general_status,
    _map_split_interval,
    _map_stroke,
    _map_workout_summary,
    _rowing_state,
    _workout_state,
)
from concept2mqtt.pm5.errors import Pm5ConnectionError, Pm5TimeoutError
from concept2mqtt.pm5.port import Pm5Port
from concept2mqtt.pm5.types import (
    Pm5Event,
    Pm5ForceCurve,
    Pm5ForceCurveEvent,
    Pm5Identity,
    Pm5SplitIntervalEvent,
    Pm5Status,
    Pm5StatusEvent,
    Pm5Stroke,
    Pm5StrokeEvent,
    Pm5WorkoutSummaryEvent,
    RowingState,
    WorkoutState,
)

# =============================================================================
# Fixtures
# =============================================================================


class FakeBleDevice:
    """Minimal stand-in for bleak.backends.device.BLEDevice."""

    def __init__(
        self, name: str = "PM5 530426599 Row", address: str = "AA:BB:CC:DD:EE:FF"
    ) -> None:
        self.name = name
        self.address = address


class FakeCharacteristic:
    """Minimal stand-in for BleakGATTCharacteristic."""

    def __init__(self, uuid: str) -> None:
        self.uuid = uuid

    @override
    def __str__(self) -> str:
        return self.uuid


class FakeAdvertisement:
    """Minimal stand-in for bleak.backends.scanner.AdvertisementData."""

    def __init__(self, service_uuids: list[str]) -> None:
        self.service_uuids = service_uuids


def _make_mock_client(
    *,
    connected: bool = True,
    identity_data: dict[str, bytes] | None = None,
) -> AsyncMock:
    """Create a mock BleakClient with configurable GATT reads."""
    client = AsyncMock()
    client.is_connected = connected

    default_identity: dict[str, bytes] = {
        "ce060011": b"PM5\x00",
        "ce060012": b"530426599",
        "ce060013": b"672",
        "ce060014": b"2.10\x00",
        "ce060015": b"Concept2\x00",
        "ce060016": b"\x01",  # RowErg
    }
    data = identity_data or default_identity

    async def fake_read(uuid: str) -> bytearray:
        # Match by the last 4 hex chars of the UUID
        key = uuid.split("-")[0][-8:]
        for k, v in data.items():
            if k in key or key in k:
                return bytearray(v)
        return bytearray(b"\x00")

    client.read_gatt_char = AsyncMock(side_effect=fake_read)
    client.write_gatt_char = AsyncMock()
    client.start_notify = AsyncMock()
    client.stop_notify = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()

    return client


@pytest.fixture
def mock_scanner() -> Generator[AsyncMock]:
    """Patch BleakScanner to return a fake PM5 device."""
    device = FakeBleDevice()
    with patch(
        "concept2mqtt.pm5.adapter.BleakScanner.find_device_by_filter",
        new_callable=AsyncMock,
        return_value=device,
    ) as scanner:
        yield scanner


@pytest.fixture
def mock_client() -> AsyncMock:
    """A mock BleakClient ready for connection."""
    return _make_mock_client()


@pytest.fixture
def adapter() -> BleakPm5Adapter:
    """A default BleakPm5Adapter (not yet connected)."""
    return BleakPm5Adapter()


async def _connect_adapter(
    adapter: BleakPm5Adapter,
    mock_scanner: AsyncMock,  # noqa: ARG001 - needed to patch scanner
    mock_client: AsyncMock,
) -> None:
    """Helper: patch BleakClient and connect the adapter."""
    with patch("concept2mqtt.pm5.adapter.BleakClient", return_value=mock_client):
        await adapter.connect()


async def _next_event(adapter: BleakPm5Adapter) -> Pm5Event:
    """Await the next event from an adapter stream."""
    return await anext(adapter.events())


# =============================================================================
# Protocol conformance
# =============================================================================


class TestProtocolConformance:
    """BleakPm5Adapter satisfies the Pm5Port Protocol.

    Technique: Specification-based Testing -- structural subtyping.
    """

    def test_adapter_satisfies_pm5port(self) -> None:
        """isinstance check against the @runtime_checkable Pm5Port."""
        adapter = BleakPm5Adapter()
        assert isinstance(adapter, Pm5Port)


# =============================================================================
# BLE scanning (c2m-bm7.1)
# =============================================================================


class TestScanning:
    """BLE scanning for PM5 devices.

    Technique: Specification-based Testing, Error Guessing.
    """

    async def test_scan_finds_pm5_by_name(
        self, adapter: BleakPm5Adapter, mock_scanner: AsyncMock, mock_client: AsyncMock
    ) -> None:
        """Scanner accepts only the expected PM5 advertisement.

        Technique: Equivalence Partitioning -- name and service identity.
        """
        with patch("concept2mqtt.pm5.adapter.BleakClient", return_value=mock_client):
            await adapter.connect()

        mock_scanner.assert_awaited_once()
        # Verify the filter function matches PM5 names
        filter_fn = mock_scanner.call_args.args[0]
        pm5_device = FakeBleDevice(name="PM5 530426599 Row")
        non_pm5 = FakeBleDevice(name="HeartRate Monitor")
        misleading_device = FakeBleDevice(name="NotPM5Sensor")
        pm5_advertisement = FakeAdvertisement(["ce060000-43e5-11e4-916c-0800200c9a66"])
        unrelated_advertisement = FakeAdvertisement(
            ["0000180d-0000-1000-8000-00805f9b34fb"]
        )
        assert filter_fn(pm5_device, pm5_advertisement) is True
        assert filter_fn(non_pm5, pm5_advertisement) is False
        assert filter_fn(misleading_device, pm5_advertisement) is False
        assert filter_fn(pm5_device, unrelated_advertisement) is False
        assert "adapter" not in mock_scanner.call_args.kwargs

    async def test_scan_raises_when_no_device_found(
        self, adapter: BleakPm5Adapter
    ) -> None:
        """Scan timeout produces Pm5ConnectionError.

        Technique: Error Guessing -- PM5 not awake.
        """
        with (
            patch(
                "concept2mqtt.pm5.adapter.BleakScanner.find_device_by_filter",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(Pm5ConnectionError, match="No PM5 found"),
        ):
            await adapter.connect()

    async def test_scan_by_address(self, mock_client: AsyncMock) -> None:
        """When address is provided, scan by address instead of filter."""
        adapter = BleakPm5Adapter(address="AA:BB:CC:DD:EE:FF")
        device = FakeBleDevice()

        with (
            patch(
                "concept2mqtt.pm5.adapter.BleakScanner.find_device_by_address",
                new_callable=AsyncMock,
                return_value=device,
            ) as scanner,
            patch("concept2mqtt.pm5.adapter.BleakClient", return_value=mock_client),
        ):
            await adapter.connect()

        scanner.assert_awaited_once()
        assert "AA:BB:CC:DD:EE:FF" in str(scanner.call_args)

    async def test_scan_timeout_is_configurable(self, mock_client: AsyncMock) -> None:
        """Custom scan_timeout is passed to BleakScanner.

        Technique: Boundary Value Analysis -- timeout configuration.
        """
        adapter = BleakPm5Adapter(scan_timeout=5.0)
        device = FakeBleDevice()

        with (
            patch(
                "concept2mqtt.pm5.adapter.BleakScanner.find_device_by_filter",
                new_callable=AsyncMock,
                return_value=device,
            ) as scanner,
            patch("concept2mqtt.pm5.adapter.BleakClient", return_value=mock_client),
        ):
            await adapter.connect()

        assert scanner.call_args.kwargs["timeout"] == 5.0


# =============================================================================
# Connection lifecycle (c2m-bm7.1)
# =============================================================================


class TestConnectionLifecycle:
    """Connect/disconnect lifecycle with bleak.

    Technique: State Transition Testing -- disconnected -> connected -> disconnected.
    """

    async def test_connect_sets_connected(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """After connect(), the adapter reports connected state."""
        await _connect_adapter(adapter, mock_scanner, mock_client)
        assert adapter._connected is True

    async def test_disconnect_clears_state(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """After disconnect(), the adapter is no longer connected."""
        await _connect_adapter(adapter, mock_scanner, mock_client)

        await adapter.disconnect()

        assert adapter._connected is False
        mock_client.disconnect.assert_awaited_once()

    async def test_connect_failure_raises(
        self, adapter: BleakPm5Adapter, mock_scanner: AsyncMock
    ) -> None:
        """BLE connect failure is wrapped as Pm5ConnectionError.

        Technique: Error Guessing -- BLE connection rejection.
        """
        failing_client = AsyncMock()
        failing_client.connect = AsyncMock(side_effect=OSError("BLE timeout"))

        with (
            patch("concept2mqtt.pm5.adapter.BleakClient", return_value=failing_client),
            pytest.raises(Pm5ConnectionError, match="BLE connect failed"),
        ):
            await adapter.connect()

    async def test_on_disconnect_callback_starts_reconnect_without_sentinel(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """BLE disconnection callback preserves the event stream for reconnect.

        Technique: State Transition Testing -- connected -> reconnecting.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)

        # Simulate bleak disconnect callback
        adapter._on_disconnect(mock_client)

        assert adapter._connected is False
        assert adapter._event_queue.empty()
        assert adapter._reconnect_task is not None
        await adapter.disconnect()

    async def test_connect_cleans_up_client_when_identity_read_fails(
        self, adapter: BleakPm5Adapter, mock_scanner: AsyncMock
    ) -> None:
        """A failed post-connect setup releases the established BLE client.

        Technique: Error Guessing -- a GATT read fails after BLE connects.
        """
        client = _make_mock_client()
        client.read_gatt_char = AsyncMock(side_effect=OSError("GATT read failed"))

        with (
            patch("concept2mqtt.pm5.adapter.BleakClient", return_value=client),
            pytest.raises(Pm5ConnectionError, match="Failed to read PM5 identity"),
        ):
            await adapter.connect()

        client.disconnect.assert_awaited_once()
        assert adapter._client is None

    async def test_reconnect_uses_bounded_exponential_backoff(self) -> None:
        """Reconnect retries double the delay only up to reconnect_max.

        Technique: Boundary Value Analysis -- minimum and maximum retry delays.
        """
        adapter = BleakPm5Adapter(reconnect_min=0.1, reconnect_max=0.2)
        adapter._running = True
        establish = AsyncMock(side_effect=[Pm5ConnectionError("lost"), None])

        with (
            patch.object(adapter, "_establish_connection", establish),
            patch(
                "concept2mqtt.pm5.adapter.asyncio.sleep", new_callable=AsyncMock
            ) as sleep,
        ):
            await adapter._reconnect()

        assert [call.args[0] for call in sleep.await_args_list] == [0.1, 0.2]


# =============================================================================
# Device identity (c2m-bm7.2)
# =============================================================================


class TestIdentityReading:
    """Reading PM5 identity from GATT characteristics.

    Technique: Specification-based Testing, Error Guessing.
    """

    async def test_identity_returns_domain_type(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """identity() returns a Pm5Identity with fields from GATT reads."""
        await _connect_adapter(adapter, mock_scanner, mock_client)

        ident = await adapter.identity()

        assert isinstance(ident, Pm5Identity)
        assert ident.serial_number == "530426599"
        assert ident.model == "PM5"
        assert ident.hardware_revision == "672"
        assert ident.firmware_revision == "2.10"
        assert ident.manufacturer == "Concept2"
        assert ident.erg_type == "RowErg"

    async def test_identity_raises_when_not_connected(
        self, adapter: BleakPm5Adapter
    ) -> None:
        """identity() before connect() raises Pm5ConnectionError.

        Technique: Error Guessing.
        """
        with pytest.raises(Pm5ConnectionError, match="not connected"):
            await adapter.identity()

    async def test_identity_is_cached(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """identity() returns the same cached value on repeated calls."""
        await _connect_adapter(adapter, mock_scanner, mock_client)

        ident1 = await adapter.identity()
        ident2 = await adapter.identity()

        assert ident1 is ident2

    async def test_identity_strips_null_bytes(
        self, adapter: BleakPm5Adapter, mock_scanner: AsyncMock
    ) -> None:
        """Null padding in GATT strings is stripped.

        Technique: Error Guessing -- real PM5 pads with NUL.
        """
        client = _make_mock_client(
            identity_data={
                "ce060011": b"PM5\x00\x00\x00",
                "ce060012": b"12345\x00\x00\x00\x00",
                "ce060013": b"1\x00\x00",
                "ce060014": b"3.0\x00",
                "ce060015": b"Concept2\x00\x00",
                "ce060016": b"\x02",  # SkiErg
            }
        )

        with patch("concept2mqtt.pm5.adapter.BleakClient", return_value=client):
            await adapter.connect()

        ident = await adapter.identity()
        assert ident.serial_number == "12345"
        assert ident.model == "PM5"
        assert ident.erg_type == "SkiErg"

    async def test_identity_mismatch_rejects_connection(
        self, mock_scanner: AsyncMock, mock_client: AsyncMock
    ) -> None:
        """Configured serial mismatch fails before exposing the PM5 connection.

        Technique: Equivalence Partitioning -- matching and non-matching identities.
        """
        adapter = BleakPm5Adapter(expected_serial_number="different")

        with (
            patch("concept2mqtt.pm5.adapter.BleakClient", return_value=mock_client),
            pytest.raises(Pm5ConnectionError, match="serial mismatch"),
        ):
            await adapter.connect()

        assert adapter._connected is False
        mock_client.disconnect.assert_awaited_once()


# =============================================================================
# Wire-to-domain mapping functions
# =============================================================================


class TestWorkoutStateMapping:
    """_workout_state maps csafe_codec int codes to domain WorkoutState.

    Technique: Equivalence Partitioning -- workout state code ranges.
    """

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            (0, WorkoutState.IDLE),
            (1, WorkoutState.ACTIVE),
            (2, WorkoutState.STARTING),
            (5, WorkoutState.ACTIVE),
            (6, WorkoutState.ACTIVE),
            (7, WorkoutState.PAUSED),
            (10, WorkoutState.FINISHED),
            (13, WorkoutState.FINISHED),
            (99, WorkoutState.UNKNOWN),
        ],
    )
    def test_workout_state_mapping(self, code: int, expected: WorkoutState) -> None:
        assert _workout_state(code) == expected


class TestRowingStateMapping:
    """_rowing_state maps csafe_codec int codes to domain RowingState.

    Technique: Equivalence Partitioning -- rowing state codes.
    """

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            (0, RowingState.INACTIVE),
            (1, RowingState.INACTIVE),
            (2, RowingState.DRIVE),
            (3, RowingState.RECOVERY),
            (4, RowingState.RECOVERY),
            (99, RowingState.UNKNOWN),
        ],
    )
    def test_rowing_state_mapping(self, code: int, expected: RowingState) -> None:
        assert _rowing_state(code) == expected


class TestMapGeneralStatus:
    """_map_general_status fuses wire-format structs into Pm5Status.

    Technique: Specification-based Testing -- unit conversion fidelity.
    """

    def _make_gs(self, **overrides: Any) -> csafe_codec.GeneralStatus:
        """Build a GeneralStatus from a standard 19-byte payload."""
        payload = bytearray(19)
        # elapsed_time_cs = 10000 (100.00s)
        payload[0:3] = (10000).to_bytes(3, "little")
        # distance_dm = 5000 (500.0m)
        payload[3:6] = (5000).to_bytes(3, "little")
        # workout_state = 5 (active)
        payload[8] = 5
        # rowing_state = 1 (drive)
        payload[9] = 1
        # stroke_state = 2 (drive)
        payload[10] = 2
        # drag_factor = 120
        payload[18] = 120
        return csafe_codec.decode_general_status(bytes(payload))

    def _make_as1(self) -> csafe_codec.AdditionalStatus1:
        """Build an AdditionalStatus1 from a 17-byte payload."""
        payload = bytearray(17)
        # elapsed_time_cs
        payload[0:3] = (10000).to_bytes(3, "little")
        # speed_mms = 4167 (4.167 m/s)
        payload[3:5] = (4167).to_bytes(2, "little")
        # stroke_rate = 28
        payload[5] = 28
        # heartrate = 155
        payload[6] = 155
        # current_pace_cs = 12000 (120.00s per 500m)
        payload[7:9] = (12000).to_bytes(2, "little")
        # average_pace_cs
        payload[9:11] = (12000).to_bytes(2, "little")
        return csafe_codec.decode_additional_status_1(bytes(payload))

    def _make_as2(self) -> csafe_codec.AdditionalStatus2:
        """Build an AdditionalStatus2 from a 20-byte payload."""
        payload = bytearray(20)
        # elapsed_time_cs
        payload[0:3] = (10000).to_bytes(3, "little")
        # interval_count
        payload[3] = 1
        # average_power = 180
        payload[4:6] = (180).to_bytes(2, "little")
        # total_calories = 42
        payload[6:8] = (42).to_bytes(2, "little")
        return csafe_codec.decode_additional_status_2(bytes(payload))

    def test_basic_conversion(self) -> None:
        """GeneralStatus alone produces Pm5Status; missing data defaults."""
        gs = self._make_gs()
        status = _map_general_status(gs, None, None)

        assert status.elapsed_time == pytest.approx(100.0)
        assert status.distance == pytest.approx(500.0)
        assert status.drag_factor == 120
        assert status.workout_state == WorkoutState.ACTIVE
        assert status.rowing_state == RowingState.DRIVE
        # Without AS1/AS2, these default to zero
        assert status.pace == 0.0
        assert status.stroke_rate == 0
        assert status.calories == 0

    def test_fused_with_additional_status(self) -> None:
        """All three sources fused into a complete Pm5Status."""
        gs = self._make_gs()
        as1 = self._make_as1()
        as2 = self._make_as2()
        status = _map_general_status(gs, as1, as2)

        assert status.elapsed_time == pytest.approx(100.0)
        assert status.distance == pytest.approx(500.0)
        assert status.pace == pytest.approx(120.0)
        assert status.speed == pytest.approx(4.167)
        assert status.stroke_rate == 28
        assert status.heart_rate == 155
        assert status.calories == 42
        assert status.power == 180
        assert status.drag_factor == 120

    def test_heart_rate_sentinel_is_normalized(self) -> None:
        """The PM5 no-belt sentinel becomes the domain's zero value.

        Technique: Equivalence Partitioning -- valid BPM versus invalid sentinel.
        """
        gs = self._make_gs()
        payload = bytearray(17)
        payload[6] = 255
        as1 = csafe_codec.decode_additional_status_1(bytes(payload))

        status = _map_general_status(gs, as1, None)

        assert status.heart_rate == 0


class TestMapStroke:
    """_map_stroke maps wire-format StrokeData to domain Pm5Stroke.

    Technique: Specification-based Testing -- unit conversion.
    """

    def _make_sd(self) -> csafe_codec.StrokeData:
        """Build a StrokeData from a 20-byte payload."""
        payload = bytearray(20)
        # elapsed_time_cs
        payload[0:3] = (10000).to_bytes(3, "little")
        # distance_dm = 980
        payload[3:6] = (980).to_bytes(3, "little")
        # drive_length = 135 (1.35m after /100)
        payload[6] = 135
        # drive_time = 85 (0.85s after /100)
        payload[7] = 85
        # stroke_recovery_time_cs = 115 (1.15s after /100)
        payload[8:10] = (115).to_bytes(2, "little")
        # stroke_distance = 98 (0.98m after /100)
        payload[10:12] = (98).to_bytes(2, "little")
        # peak_drive_force = 4500 (450.0 lb converted to N)
        payload[12:14] = (4500).to_bytes(2, "little")
        # average_drive_force = 3200 (320.0 lb converted to N)
        payload[14:16] = (3200).to_bytes(2, "little")
        # work_per_stroke = 2850 (285.0J after /10)
        payload[16:18] = (2850).to_bytes(2, "little")
        # stroke_count = 10
        payload[18:20] = (10).to_bytes(2, "little")
        return csafe_codec.decode_stroke_data(bytes(payload))

    def _make_asd(self) -> csafe_codec.AdditionalStrokeData:
        """Build an AdditionalStrokeData from a 15-byte payload."""
        payload = bytearray(15)
        # elapsed_time_cs
        payload[0:3] = (10000).to_bytes(3, "little")
        # stroke_power = 190
        payload[3:5] = (190).to_bytes(2, "little")
        # stroke_calories = 3500 cal/hr
        payload[5:7] = (3500).to_bytes(2, "little")
        # stroke_count = 10
        payload[7:9] = (10).to_bytes(2, "little")
        return csafe_codec.decode_additional_stroke_data(bytes(payload))

    def test_stroke_mapping(self) -> None:
        """StrokeData fields are converted to SI units."""
        sd = self._make_sd()
        stroke = _map_stroke(sd, None)

        assert stroke.stroke_count == 10
        assert stroke.drive_time == pytest.approx(0.85)
        assert stroke.recovery_time == pytest.approx(1.15)
        assert stroke.drive_length == pytest.approx(1.35)
        assert stroke.stroke_distance == pytest.approx(0.98)
        assert stroke.peak_force == pytest.approx(2001.699726867225)
        assert stroke.average_force == pytest.approx(1423.43091688336)
        assert stroke.work_per_stroke == pytest.approx(285.0)
        assert stroke.stroke_power == 0  # No ASD
        assert stroke.stroke_calories == 0.0

    def test_stroke_mapping_with_additional(self) -> None:
        """StrokeData + AdditionalStrokeData fused correctly."""
        sd = self._make_sd()
        asd = self._make_asd()
        stroke = _map_stroke(sd, asd)

        assert stroke.stroke_power == 190
        assert stroke.stroke_calories == pytest.approx(0.0019444444444444444)


class TestMapWorkoutSummary:
    """_map_workout_summary maps EndOfWorkoutSummary to domain type.

    Technique: Specification-based Testing.
    """

    def test_summary_mapping(self) -> None:
        payload = bytearray(20)
        # log_entry_date, log_entry_time = 0
        # elapsed_time_cs = 180000 (30 min)
        payload[4:7] = (180000).to_bytes(3, "little")
        # distance_dm = 60000 (6000m)
        payload[7:10] = (60000).to_bytes(3, "little")
        # avg_stroke_rate = 26 (byte 10)
        payload[10] = 26
        # avg_heartrate = 160 (byte 12)
        payload[12] = 160
        # avg_drag_factor = 120 (byte 15)
        payload[15] = 120
        # avg_pace_ds = 250 (25.0s per 500m, 2 bytes at offset 18)
        payload[18:20] = (250).to_bytes(2, "little")
        summary = csafe_codec.decode_end_of_workout_summary(bytes(payload))
        result = _map_workout_summary(summary)

        assert result.elapsed_time == pytest.approx(1800.0)
        assert result.distance == pytest.approx(6000.0)
        assert result.avg_pace == pytest.approx(25.0)
        assert result.avg_stroke_rate == 26
        assert result.avg_heart_rate == 160
        assert result.avg_drag_factor == 120


class TestMapSplitInterval:
    """_map_split_interval maps SplitIntervalData to domain type.

    Technique: Specification-based Testing.
    """

    def test_split_mapping(self) -> None:
        payload = bytearray(18)
        # elapsed_time_cs = 60000 (600s)
        payload[0:3] = (60000).to_bytes(3, "little")
        # distance_dm = 20000 (2000m)
        payload[3:6] = (20000).to_bytes(3, "little")
        # split_interval_number = 1 (byte 17)
        payload[17] = 1
        split = csafe_codec.decode_split_interval_data(bytes(payload))
        result = _map_split_interval(split)

        assert result.number == 1
        assert result.elapsed_time == pytest.approx(600.0)
        assert result.distance == pytest.approx(2000.0)


# =============================================================================
# Notification subscription and event streaming (c2m-bm7.3)
# =============================================================================


class TestNotificationSubscription:
    """Notification subscription on PM5 streaming characteristics.

    Technique: Specification-based Testing.
    """

    async def test_subscribe_calls_start_notify(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """connect() subscribes to streaming characteristics."""
        await _connect_adapter(adapter, mock_scanner, mock_client)

        # Should have called start_notify for each streaming UUID + PM TX
        assert mock_client.start_notify.await_count >= 10
        subscribed_uuids = [
            call.args[0] for call in mock_client.start_notify.call_args_list
        ]
        assert any("003d" in uuid for uuid in subscribed_uuids)

    async def test_subscribe_skips_unavailable_chars(
        self, adapter: BleakPm5Adapter, mock_scanner: AsyncMock
    ) -> None:
        """Unavailable characteristics are skipped without error.

        Technique: Error Guessing -- firmware-dependent characteristics.
        """
        client = _make_mock_client()
        call_count = 0

        original_start_notify = client.start_notify

        async def flaky_start_notify(uuid: str, callback: Any) -> None:
            nonlocal call_count
            call_count += 1
            # Fail on the third subscription
            if call_count == 3:
                raise Exception("BleakCharacteristicNotFoundError")
            return await original_start_notify(uuid, callback)

        client.start_notify = AsyncMock(side_effect=flaky_start_notify)

        with patch("concept2mqtt.pm5.adapter.BleakClient", return_value=client):
            await adapter.connect()

        # Should still be connected despite one failed subscription
        assert adapter._connected is True


class TestEventStreaming:
    """Event streaming from BLE notifications.

    Technique: Specification-based Testing, State Transition Testing.
    """

    async def test_general_status_notification_produces_event(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """A GeneralStatus notification becomes a Pm5StatusEvent."""
        await _connect_adapter(adapter, mock_scanner, mock_client)

        # Simulate a notification
        payload = bytearray(19)
        payload[0:3] = (10000).to_bytes(3, "little")  # elapsed_time_cs
        payload[3:6] = (5000).to_bytes(3, "little")  # distance_dm
        payload[8] = 5  # workout_state = active
        payload[9] = 1  # rowing_state = drive
        payload[18] = 120  # drag_factor

        sender = FakeCharacteristic("ce060031-43e5-11e4-916c-0800200c9a66")
        adapter._on_notification(sender, bytearray(payload))

        event = await _next_event(adapter)
        assert isinstance(event, Pm5StatusEvent)
        assert event.status.elapsed_time == pytest.approx(100.0)
        assert event.status.distance == pytest.approx(500.0)
        assert event.status.workout_state == WorkoutState.ACTIVE

    async def test_stroke_notification_produces_event(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """A StrokeData notification becomes a Pm5StrokeEvent."""
        await _connect_adapter(adapter, mock_scanner, mock_client)

        payload = bytearray(20)
        payload[18:20] = (5).to_bytes(2, "little")  # stroke_count

        sender = FakeCharacteristic("ce060035-43e5-11e4-916c-0800200c9a66")
        adapter._on_notification(sender, bytearray(payload))

        event = adapter._event_queue.get_nowait()
        assert isinstance(event, Pm5StrokeEvent)
        assert event.stroke.stroke_count == 5

    async def test_force_curve_notifications_assemble_chunks_by_sequence(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """Out-of-order chunks emit one complete force curve in sequence order.

        Technique: State Transition Testing -- incomplete -> complete curve.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)
        sender = FakeCharacteristic("ce06003d-43e5-11e4-916c-0800200c9a66")

        adapter._on_notification(sender, bytearray(b"\x22\x01\x1e\x00\x28\x00"))
        assert adapter._event_queue.empty()
        adapter._on_notification(sender, bytearray(b"\x22\x00\x0a\x00\x14\x00"))

        event = adapter._event_queue.get_nowait()
        assert isinstance(event, Pm5ForceCurveEvent)
        assert event.force_curve.data_points == (10, 20, 30, 40)

    async def test_status_boundaries_survive_telemetry_coalescing(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """High-rate telemetry cannot overwrite distinct status boundaries.

        Technique: State Transition Testing -- ACTIVE -> PAUSED survives a burst.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)
        active = Pm5StatusEvent(
            Pm5Status(0, 0, 0, 0, 0, 0, 0, 0, 0, WorkoutState.ACTIVE, RowingState.DRIVE)
        )
        paused = Pm5StatusEvent(
            Pm5Status(
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                WorkoutState.PAUSED,
                RowingState.INACTIVE,
            )
        )
        adapter._enqueue_event(active)
        adapter._enqueue_event(Pm5StrokeEvent(Pm5Stroke(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)))
        adapter._enqueue_event(paused)
        adapter._enqueue_event(Pm5ForceCurveEvent(Pm5ForceCurve((1, 2))))

        stream = adapter.events()
        events = [await anext(stream) for _ in range(3)]
        await stream.aclose()

        assert [
            event.status.workout_state
            for event in events
            if isinstance(event, Pm5StatusEvent)
        ] == [WorkoutState.ACTIVE, WorkoutState.PAUSED]
        assert isinstance(events[-1], Pm5ForceCurveEvent)

    async def test_events_continue_after_automatic_reconnect(
        self, mock_scanner: AsyncMock
    ) -> None:
        """An event consumer survives a reconnect and receives fresh telemetry.

        Technique: State Transition Testing -- connected -> lost -> reconnected.
        """
        adapter = BleakPm5Adapter(reconnect_min=0.0, reconnect_max=0.0)
        first_client = _make_mock_client()
        second_client = _make_mock_client()
        with patch(
            "concept2mqtt.pm5.adapter.BleakClient",
            side_effect=[first_client, second_client],
        ):
            await adapter.connect()
            next_event = asyncio.create_task(_next_event(adapter))
            adapter._on_disconnect(first_client)
            assert adapter._reconnect_task is not None
            await adapter._reconnect_task

        sender = FakeCharacteristic("ce060031-43e5-11e4-916c-0800200c9a66")
        payload = bytearray(19)
        payload[0:3] = (100).to_bytes(3, "little")
        adapter._on_notification(sender, payload)

        event = await next_event
        assert isinstance(event, Pm5StatusEvent)
        assert adapter._connected is True
        await adapter.disconnect()

    async def test_connect_discards_stale_disconnect_sentinel(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """A fresh connection cannot immediately end on an earlier stop signal.

        Technique: State Transition Testing -- stopped -> connected event stream.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)
        await adapter.disconnect()
        await _connect_adapter(adapter, mock_scanner, mock_client)
        next_event = asyncio.create_task(_next_event(adapter))
        sender = FakeCharacteristic("ce060031-43e5-11e4-916c-0800200c9a66")

        adapter._on_notification(sender, bytearray(19))

        assert isinstance(await next_event, Pm5StatusEvent)
        await adapter.disconnect()

    async def test_unknown_uuid_is_ignored(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """Notifications from unknown UUIDs are silently dropped.

        Technique: Error Guessing -- unexpected UUID.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)

        sender = FakeCharacteristic("00001234-0000-1000-8000-00805f9b34fb")
        adapter._on_notification(sender, bytearray(b"\x00" * 19))

        assert adapter._event_queue.empty()

    async def test_malformed_notification_is_dropped(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """Notifications that fail to decode are dropped without crashing.

        Technique: Error Guessing -- truncated payload.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)

        sender = FakeCharacteristic("ce060031-43e5-11e4-916c-0800200c9a66")
        # Too short for GeneralStatus (needs 19 bytes)
        adapter._on_notification(sender, bytearray(b"\x00" * 5))

        assert adapter._event_queue.empty()

    async def test_events_iterator_ends_on_disconnect(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """events() stops iterating when disconnect is called.

        Technique: State Transition Testing -- stream termination.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)

        collected: list[Pm5Event] = []

        async def consume() -> None:
            async for event in adapter.events():
                collected.append(event)

        task = asyncio.create_task(consume())
        # Let the consumer start waiting
        await asyncio.sleep(0.01)
        await adapter.disconnect()
        await task

        # No events expected (none were injected)
        assert collected == []

    async def test_workout_summary_notification(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """EndOfWorkoutSummary notification produces Pm5WorkoutSummaryEvent."""
        await _connect_adapter(adapter, mock_scanner, mock_client)

        payload = bytearray(20)
        payload[4:7] = (180000).to_bytes(3, "little")  # elapsed_time_cs

        sender = FakeCharacteristic("ce060039-43e5-11e4-916c-0800200c9a66")
        adapter._on_notification(sender, bytearray(payload))

        event = adapter._event_queue.get_nowait()
        assert isinstance(event, Pm5WorkoutSummaryEvent)

    async def test_split_interval_notification(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """SplitIntervalData notification produces Pm5SplitIntervalEvent."""
        await _connect_adapter(adapter, mock_scanner, mock_client)

        payload = bytearray(18)
        payload[14] = 1  # split_interval_number

        sender = FakeCharacteristic("ce060037-43e5-11e4-916c-0800200c9a66")
        adapter._on_notification(sender, bytearray(payload))

        event = adapter._event_queue.get_nowait()
        assert isinstance(event, Pm5SplitIntervalEvent)


# =============================================================================
# CSAFE request/response (c2m-bm7.4)
# =============================================================================


class TestCsafeRequestResponse:
    """CSAFE command/response over BLE.

    Technique: Specification-based Testing, Boundary Value Analysis.
    """

    async def test_csafe_transport_writes_and_reads(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """The CSAFE transport writes to PM RX and reads from PM TX."""
        await _connect_adapter(adapter, mock_scanner, mock_client)

        # Simulate response arriving shortly after write
        async def respond_after_write(*args: Any, **kwargs: Any) -> None:
            await asyncio.sleep(0.01)
            adapter._csafe_response_data = b"\xf1\x01\x00\xf2"
            adapter._csafe_response.set()

        mock_client.write_gatt_char = AsyncMock(side_effect=respond_after_write)

        response = await adapter._send_csafe(b"\xf1\x80\xf2")

        assert response == b"\xf1\x01\x00\xf2"

    async def test_csafe_transport_raises_when_not_connected(
        self, adapter: BleakPm5Adapter
    ) -> None:
        """The CSAFE transport before connect() raises Pm5ConnectionError."""
        with pytest.raises(Pm5ConnectionError, match="not connected"):
            await adapter._send_csafe(b"\xf1\x80\xf2")

    async def test_csafe_transport_times_out(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """CSAFE response timeout raises Pm5TimeoutError.

        Technique: Boundary Value Analysis -- timeout edge.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)

        # Patch the timeout to be very short
        import concept2mqtt.pm5.adapter as adapter_mod

        original = adapter_mod.DEFAULT_CSAFE_TIMEOUT
        adapter_mod.DEFAULT_CSAFE_TIMEOUT = 0.05
        try:
            with pytest.raises(Pm5TimeoutError, match="CSAFE response timeout"):
                await adapter._send_csafe(b"\xf1\x80\xf2")
        finally:
            adapter_mod.DEFAULT_CSAFE_TIMEOUT = original

    async def test_csafe_transport_wraps_write_failure(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """CSAFE write failure raises Pm5ConnectionError.

        Technique: Error Guessing -- BLE write rejection.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)
        mock_client.write_gatt_char = AsyncMock(side_effect=OSError("write rejected"))

        with pytest.raises(Pm5ConnectionError, match="CSAFE write failed"):
            await adapter._send_csafe(b"\xf1\x80\xf2")

    async def test_csafe_transport_splits_writes_at_twenty_bytes(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """Frames larger than one ATT payload are written in 20-byte chunks.

        Technique: Boundary Value Analysis -- 20-byte BLE payload limit.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)
        command = bytes(range(21))

        async def respond_after_last_chunk(
            _uuid: str, data: bytes, **_kwargs: Any
        ) -> None:
            if data == command[20:]:
                adapter._csafe_response_data = b"response"
                adapter._csafe_response.set()

        mock_client.write_gatt_char = AsyncMock(side_effect=respond_after_last_chunk)

        response = await adapter._send_csafe(command)

        assert response == b"response"
        writes = [call.args[1] for call in mock_client.write_gatt_char.call_args_list]
        assert writes == [
            command[:20],
            command[20:],
        ]

    async def test_csafe_transport_serializes_concurrent_requests(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """A second request cannot overwrite the first request's response state.

        Technique: Condition Coverage -- concurrent callers share one transport.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)
        first_write_started = asyncio.Event()
        release_first_write = asyncio.Event()
        write_count = 0

        async def respond_in_order(*_args: Any, **_kwargs: Any) -> None:
            nonlocal write_count
            write_count += 1
            if write_count == 1:
                first_write_started.set()
                await release_first_write.wait()
            adapter._csafe_response_data = bytes([write_count])
            adapter._csafe_response.set()

        mock_client.write_gatt_char = AsyncMock(side_effect=respond_in_order)
        first = asyncio.create_task(adapter._send_csafe(b"first"))
        await first_write_started.wait()
        second = asyncio.create_task(adapter._send_csafe(b"second"))
        await asyncio.sleep(0)
        assert mock_client.write_gatt_char.await_count == 1

        release_first_write.set()

        assert await first == b"\x01"
        assert await second == b"\x02"


# =============================================================================
# Notification rate configuration (c2m-bm7.5)
# =============================================================================


class TestNotificationRate:
    """Notification rate configuration via char 0x0034.

    Technique: Specification-based Testing, Boundary Value Analysis.
    """

    async def test_set_notification_rate_writes_single_byte(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """set_notification_rate writes exactly 1 byte (not 8).

        Hardware finding: PM5 rejects >1 byte writes to ce060034.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)
        mock_client.read_gatt_char = AsyncMock(return_value=bytearray(b"\x02"))

        result = await adapter.set_notification_rate(2)

        write_call = mock_client.write_gatt_char.call_args
        assert write_call.args[1] == b"\x02"
        assert len(write_call.args[1]) == 1
        assert result == 2

    async def test_set_notification_rate_masks_to_byte(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """Values > 255 are masked to a single byte.

        Technique: Boundary Value Analysis -- overflow.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)
        mock_client.read_gatt_char = AsyncMock(return_value=bytearray(b"\x00"))

        await adapter.set_notification_rate(256)

        write_call = mock_client.write_gatt_char.call_args
        assert write_call.args[1] == b"\x00"  # 256 & 0xFF = 0

    async def test_set_notification_rate_raises_when_not_connected(
        self, adapter: BleakPm5Adapter
    ) -> None:
        """set_notification_rate before connect() raises Pm5ConnectionError."""
        with pytest.raises(Pm5ConnectionError, match="not connected"):
            await adapter.set_notification_rate(2)

    async def test_set_notification_rate_read_back_failure_returns_written_byte(
        self,
        adapter: BleakPm5Adapter,
        mock_scanner: AsyncMock,
        mock_client: AsyncMock,
    ) -> None:
        """If read-back fails, returns the masked byte that was written.

        Technique: Error Guessing -- read-back failure.
        """
        await _connect_adapter(adapter, mock_scanner, mock_client)

        # Write succeeds, but the second read_gatt_char (read-back) fails
        call_count = 0
        original = mock_client.read_gatt_char

        async def fail_on_readback(uuid: str) -> bytearray:
            nonlocal call_count
            call_count += 1
            # Identity reads happen during connect; the rate read-back is later
            if "0034" in uuid:
                raise OSError("read failed")
            return await original(uuid)

        mock_client.read_gatt_char = AsyncMock(side_effect=fail_on_readback)

        result = await adapter.set_notification_rate(256)
        assert result == 0
