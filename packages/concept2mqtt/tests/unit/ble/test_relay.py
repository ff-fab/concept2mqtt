"""Unit tests for concept2mqtt/ble/relay.py — byte-level PM5 relay core.

Test Techniques Used:
- State Transition Testing: relay lifecycle (idle -> started -> stopped)
- Specification-based Testing: pass-through fidelity in both directions
- Branch Coverage: readable/writable guards, tap present/absent, notify failure
- Error Guessing: unknown UUIDs, wrong-direction access, disconnected consumer
- Boundary Value Analysis: empty payloads, DEBUG/INFO log level threshold
"""

from __future__ import annotations

import logging

import pytest
from tests.fixtures.ble import FakeCentralLink, FakePeripheralServer

from concept2mqtt.ble.errors import (
    CharacteristicAccessError,
    UnknownCharacteristicError,
)
from concept2mqtt.ble.profile import get_profile, pm5_uuid
from concept2mqtt.ble.relay import BleRelay

GENERAL_STATUS = pm5_uuid(0x0031)
CSAFE_RECEIVE = pm5_uuid(0x0021)
CSAFE_TRANSMIT = pm5_uuid(0x0022)
SAMPLE_RATE = pm5_uuid(0x0034)
SERIAL_NUMBER = pm5_uuid(0x0012)
HEART_RATE_RECEIVE = pm5_uuid(0x0041)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def central() -> FakeCentralLink:
    """Fake PM5 with a serial number and a sample rate available to read."""
    return FakeCentralLink(values={SERIAL_NUMBER: b"530426599", SAMPLE_RATE: b"\x01"})


@pytest.fixture
def peripheral() -> FakePeripheralServer:
    """Fake emulated-PM5 GATT server."""
    return FakePeripheralServer()


@pytest.fixture
def relay(central: FakeCentralLink, peripheral: FakePeripheralServer) -> BleRelay:
    """Relay wired to the fakes with the default proprietary profile."""
    return BleRelay(central=central, peripheral=peripheral, profile=get_profile())


@pytest.fixture
async def started_relay(relay: BleRelay) -> BleRelay:
    """Relay that has completed startup."""
    await relay.start()
    return relay


# =============================================================================
# Lifecycle
# =============================================================================


class TestLifecycle:
    """Startup subscribes to the PM5 before advertising; stop unwinds both.

    Technique: State Transition Testing — idle -> started -> stopped.
    """

    async def test_start_subscribes_to_every_streaming_characteristic(
        self, started_relay: BleRelay, central: FakeCentralLink
    ) -> None:
        expected = {c.uuid for c in get_profile() if c.streaming}

        assert set(central.subscriptions) == expected
        assert set(started_relay.subscribed) == expected

    async def test_start_does_not_subscribe_to_write_only_characteristics(
        self, started_relay: BleRelay, central: FakeCentralLink
    ) -> None:
        assert CSAFE_RECEIVE not in central.subscriptions

    async def test_start_registers_the_profile_with_the_peripheral(
        self, started_relay: BleRelay, peripheral: FakePeripheralServer
    ) -> None:
        assert peripheral.running is True
        assert peripheral.profile is not None
        assert peripheral.profile.name == "pm5-proprietary"

    async def test_start_does_not_read_the_pm5_eagerly(
        self, started_relay: BleRelay, central: FakeCentralLink
    ) -> None:
        """Identity reads are lazy — startup costs no PM5 round trips.

        Technique: Error Guessing — eager priming would fail the whole relay
        on any characteristic an older firmware does not implement.
        """
        assert central.reads == []

    async def test_stop_unsubscribes_and_stops_advertising(
        self,
        started_relay: BleRelay,
        central: FakeCentralLink,
        peripheral: FakePeripheralServer,
    ) -> None:
        await started_relay.stop()

        assert central.subscriptions == {}
        assert peripheral.running is False
        assert started_relay.subscribed == ()


class TestFirmwareVarianceTolerance:
    """A characteristic the firmware lacks costs only that one stream.

    The spec marks several characteristics as firmware-version dependent, so a
    failed subscription is expected rather than exceptional.

    Technique: Error Guessing — partial GATT support on older PM5 firmware.
    """

    @pytest.fixture
    def central(self) -> FakeCentralLink:
        return FakeCentralLink(unavailable={CSAFE_TRANSMIT})

    async def test_start_completes_despite_unavailable_characteristic(
        self, started_relay: BleRelay, peripheral: FakePeripheralServer
    ) -> None:
        assert peripheral.running is True
        assert started_relay.stats.unavailable_characteristics == 1

    async def test_unavailable_characteristic_is_not_subscribed(
        self, started_relay: BleRelay
    ) -> None:
        assert CSAFE_TRANSMIT not in started_relay.subscribed

    async def test_remaining_characteristics_still_relay(
        self,
        started_relay: BleRelay,
        central: FakeCentralLink,
        peripheral: FakePeripheralServer,
    ) -> None:
        await central.emit(GENERAL_STATUS, b"\x07")

        assert peripheral.notifications == [(GENERAL_STATUS, b"\x07")]

    async def test_stop_only_unsubscribes_what_was_subscribed(
        self, started_relay: BleRelay, central: FakeCentralLink
    ) -> None:
        await started_relay.stop()

        assert central.subscriptions == {}


# =============================================================================
# PM5 -> consumer (notifications)
# =============================================================================


class TestNotificationRelay:
    """Notifications are forwarded byte-for-byte without interpretation.

    Technique: Specification-based Testing — raw pass-through per ADR-003.
    """

    async def test_notification_is_forwarded_unmodified(
        self,
        started_relay: BleRelay,
        central: FakeCentralLink,
        peripheral: FakePeripheralServer,
    ) -> None:
        payload = bytes(range(19))

        await central.emit(GENERAL_STATUS, payload)

        assert peripheral.notifications == [(GENERAL_STATUS, payload)]

    async def test_empty_notification_is_forwarded(
        self,
        started_relay: BleRelay,
        central: FakeCentralLink,
        peripheral: FakePeripheralServer,
    ) -> None:
        """Technique: Boundary Value Analysis — zero-length payload."""
        await central.emit(GENERAL_STATUS, b"")

        assert peripheral.notifications == [(GENERAL_STATUS, b"")]

    async def test_payload_is_not_aliased_to_the_transport_buffer(
        self,
        started_relay: BleRelay,
        central: FakeCentralLink,
        peripheral: FakePeripheralServer,
    ) -> None:
        """BLE stacks hand over mutable buffers they are free to reuse.

        Technique: Error Guessing — an aliased buffer would silently corrupt
        already-delivered notifications.
        """
        buffer = bytearray(b"\x01\x02")

        await central.emit(GENERAL_STATUS, buffer)
        buffer[0] = 0xFF

        assert peripheral.notifications == [(GENERAL_STATUS, b"\x01\x02")]

    async def test_csafe_responses_are_relayed_as_notifications(
        self,
        started_relay: BleRelay,
        central: FakeCentralLink,
        peripheral: FakePeripheralServer,
    ) -> None:
        await central.emit(CSAFE_TRANSMIT, b"\xf1\x80\x81")

        assert peripheral.notifications == [(CSAFE_TRANSMIT, b"\xf1\x80\x81")]

    async def test_notifications_increment_the_relay_counter(
        self, started_relay: BleRelay, central: FakeCentralLink
    ) -> None:
        await central.emit(GENERAL_STATUS, b"\x00")
        await central.emit(GENERAL_STATUS, b"\x01")

        assert started_relay.stats.notifications_relayed == 2


class TestNotificationTap:
    """The MQTT path taps the same notification stream as the relay.

    Technique: Branch Coverage — tap present vs. absent.
    """

    async def test_tap_receives_every_notification(
        self, central: FakeCentralLink, peripheral: FakePeripheralServer
    ) -> None:
        tapped: list[tuple[str, bytes]] = []

        async def tap(uuid: str, data: bytes) -> None:
            tapped.append((uuid, data))

        relay = BleRelay(
            central=central,
            peripheral=peripheral,
            profile=get_profile(),
            tap=tap,
        )
        await relay.start()

        await central.emit(GENERAL_STATUS, b"\x2a")

        assert tapped == [(GENERAL_STATUS, b"\x2a")]

    async def test_tap_still_runs_when_the_consumer_delivery_fails(
        self, central: FakeCentralLink
    ) -> None:
        """MQTT publishing must survive a broken BLE consumer (criterion 4)."""
        tapped: list[tuple[str, bytes]] = []

        async def tap(uuid: str, data: bytes) -> None:
            tapped.append((uuid, data))

        peripheral = FakePeripheralServer(notify_error=RuntimeError("disconnected"))
        relay = BleRelay(
            central=central,
            peripheral=peripheral,
            profile=get_profile(),
            tap=tap,
        )
        await relay.start()

        await central.emit(GENERAL_STATUS, b"\x2a")

        assert tapped == [(GENERAL_STATUS, b"\x2a")]
        assert relay.stats.notify_errors == 1
        assert relay.stats.notifications_relayed == 0


class TestNotificationFailureIsolation:
    """A failing consumer must never tear down the sole PM5 connection.

    Technique: Error Guessing — the relay is a single point of failure for all
    PM5 connectivity (ADR-003), so delivery errors are contained.
    """

    async def test_delivery_failure_is_swallowed_and_counted(
        self, central: FakeCentralLink
    ) -> None:
        peripheral = FakePeripheralServer(notify_error=RuntimeError("disconnected"))
        relay = BleRelay(central=central, peripheral=peripheral, profile=get_profile())
        await relay.start()

        await central.emit(GENERAL_STATUS, b"\x00")

        assert relay.stats.notify_errors == 1


# =============================================================================
# Consumer -> PM5 (writes)
# =============================================================================


class TestWriteRelay:
    """Writes from the emulated peripheral reach the real PM5.

    Technique: Specification-based Testing — criterion 3 of c2m-ooz.3.
    """

    async def test_csafe_command_is_forwarded_with_response(
        self,
        started_relay: BleRelay,
        central: FakeCentralLink,
        peripheral: FakePeripheralServer,
    ) -> None:
        await peripheral.write(CSAFE_RECEIVE, b"\xf1\x76\xf2")

        assert central.writes == [(CSAFE_RECEIVE, b"\xf1\x76\xf2", True)]

    async def test_heart_rate_write_is_forwarded(
        self,
        started_relay: BleRelay,
        peripheral: FakePeripheralServer,
        central: FakeCentralLink,
    ) -> None:
        await peripheral.write(HEART_RATE_RECEIVE, b"\x00\x48")

        assert central.writes == [(HEART_RATE_RECEIVE, b"\x00\x48", True)]

    async def test_write_increments_the_relay_counter(
        self, started_relay: BleRelay, peripheral: FakePeripheralServer
    ) -> None:
        await peripheral.write(CSAFE_RECEIVE, b"\x01")

        assert started_relay.stats.writes_relayed == 1

    async def test_write_to_read_only_characteristic_is_rejected(
        self,
        started_relay: BleRelay,
        peripheral: FakePeripheralServer,
        central: FakeCentralLink,
    ) -> None:
        with pytest.raises(CharacteristicAccessError, match="write"):
            await peripheral.write(SERIAL_NUMBER, b"spoofed")

        assert central.writes == []

    async def test_write_to_unknown_uuid_is_rejected(
        self, started_relay: BleRelay, peripheral: FakePeripheralServer
    ) -> None:
        with pytest.raises(UnknownCharacteristicError):
            await peripheral.write("00000000-0000-0000-0000-000000000000", b"\x00")


# =============================================================================
# Consumer -> PM5 (reads)
# =============================================================================


class TestReadRelay:
    """Reads are served from a lazily populated read-through cache.

    Technique: Branch Coverage — cache miss vs. cache hit.
    """

    async def test_first_read_fetches_from_the_pm5(
        self,
        started_relay: BleRelay,
        peripheral: FakePeripheralServer,
        central: FakeCentralLink,
    ) -> None:
        value = await peripheral.read(SERIAL_NUMBER)

        assert value == b"530426599"
        assert central.reads == [SERIAL_NUMBER]

    async def test_repeat_read_is_served_from_cache(
        self,
        started_relay: BleRelay,
        peripheral: FakePeripheralServer,
        central: FakeCentralLink,
    ) -> None:
        await peripheral.read(SERIAL_NUMBER)
        await peripheral.read(SERIAL_NUMBER)

        assert central.reads == [SERIAL_NUMBER]
        assert started_relay.stats.reads_served == 2

    async def test_read_lookup_is_case_insensitive(
        self, started_relay: BleRelay, peripheral: FakePeripheralServer
    ) -> None:
        assert await peripheral.read(SERIAL_NUMBER.upper()) == b"530426599"

    async def test_read_of_write_only_characteristic_is_rejected(
        self, started_relay: BleRelay, peripheral: FakePeripheralServer
    ) -> None:
        with pytest.raises(CharacteristicAccessError, match="read"):
            await peripheral.read(CSAFE_RECEIVE)

    async def test_read_of_unknown_uuid_is_rejected(
        self, started_relay: BleRelay, peripheral: FakePeripheralServer
    ) -> None:
        with pytest.raises(UnknownCharacteristicError):
            await peripheral.read("00000000-0000-0000-0000-000000000000")


class TestGattAccessLogging:
    """Peripheral-side access is logged at DEBUG, identifying the UUID touched.

    The Pi is the GATT server the app connects to, so this log — not an
    external sniffer — is the evidence for which service a connecting app
    queries (hardware validation Step B).

    Technique: Specification-based Testing — the log is a documented artifact
    of the validation procedure, not incidental output.
    """

    async def test_read_logs_the_characteristic_at_debug(
        self,
        started_relay: BleRelay,
        peripheral: FakePeripheralServer,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Arrange
        caplog.set_level(logging.DEBUG, logger="concept2mqtt.ble.relay")

        # Act
        await peripheral.read(SERIAL_NUMBER)

        # Assert
        assert SERIAL_NUMBER in caplog.text
        assert "Serial Number String" in caplog.text

    async def test_write_logs_the_characteristic_at_debug(
        self,
        started_relay: BleRelay,
        peripheral: FakePeripheralServer,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Arrange
        caplog.set_level(logging.DEBUG, logger="concept2mqtt.ble.relay")

        # Act
        await peripheral.write(CSAFE_RECEIVE, b"\xf1\x76\xf2")

        # Assert
        assert CSAFE_RECEIVE in caplog.text
        assert "3 bytes" in caplog.text

    async def test_rejected_access_is_still_logged(
        self,
        started_relay: BleRelay,
        peripheral: FakePeripheralServer,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """An app probing a wrong-direction characteristic is evidence too.

        Technique: Error Guessing — logging only successful access would hide
        exactly the mismatches Step B exists to detect.
        """
        # Arrange
        caplog.set_level(logging.DEBUG, logger="concept2mqtt.ble.relay")

        # Act
        with pytest.raises(CharacteristicAccessError):
            await peripheral.read(CSAFE_RECEIVE)

        # Assert
        assert CSAFE_RECEIVE in caplog.text

    async def test_access_is_silent_above_debug_level(
        self,
        started_relay: BleRelay,
        peripheral: FakePeripheralServer,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Per-access logging must stay opt-in — a session is thousands of them.

        Technique: Boundary Value Analysis — INFO is the level below which the
        access log is suppressed.
        """
        # Arrange
        caplog.set_level(logging.INFO, logger="concept2mqtt.ble.relay")

        # Act
        await peripheral.read(SERIAL_NUMBER)

        # Assert
        assert caplog.records == []


class TestCacheCoherence:
    """A relayed write updates the cached value it overwrites.

    Technique: State Transition Testing — cached -> written -> re-read.
    """

    async def test_write_to_readable_characteristic_refreshes_cache(
        self,
        started_relay: BleRelay,
        peripheral: FakePeripheralServer,
        central: FakeCentralLink,
    ) -> None:
        assert await peripheral.read(SAMPLE_RATE) == b"\x01"

        await peripheral.write(SAMPLE_RATE, b"\x03")

        assert await peripheral.read(SAMPLE_RATE) == b"\x03"
        assert central.reads == [SAMPLE_RATE]
