"""PM5 BLE peripheral relay — hardware validation harness for c2m-ooz.3.

Holds the sole BLE connection to a real PM5 on one adapter (central role) and
re-serves it as an emulated PM5 GATT server on a second adapter (peripheral
role), so a BLE-native consumer such as the official Concept2 iPhone app can
connect to the Pi instead of the erg. See ADR-003.

The relay logic itself lives in ``concept2mqtt.ble`` and is unit tested. This
script is only the hardware binding — bleak on the central side, bluez-
peripheral on the peripheral side — plus a runner. It exists because none of
the acceptance criteria for c2m-ooz.3 can be verified without a real PM5, two
adapters and an iPhone.

Prerequisites
    - Kernel past the raspberrypi/linux#7473 LEAdvertisingManager1 regression
      (``uname -r`` must be >= 6.18.42-v8+; ``rpi-update`` if not).
    - Two BLE adapters: hci0 (onboard, central) and hci1 (CSR8510-class USB
      dongle, peripheral). Both powered: ``bluetoothctl power on``.
    - PM5 awake (pull the handle) and NOT connected to anything else.
    - Dependencies: ``uv run --with bleak --with bluez-peripheral python ...``

Run
    uv run --with bleak --with bluez-peripheral \\
        python docs/planning/legacy/examples/relay_pm5.py

    Options:
      --profile pm5-proprietary|ftms   GATT profile to emulate (default:
                                       pm5-proprietary; switch to ftms if the
                                       run log shows the app queries the
                                       standard Fitness Machine Service)
      --central hci0                   adapter holding the real PM5 link
      --peripheral hci1                adapter running the emulated PM5
      --debug                          log every GATT read/write the connected
                                       app performs (Step B evidence)

Then follow ``docs/testing/pm5-ble-relay-hardware-validation.md`` for the
per-criterion checklist and the GATT-access capture procedure.

Known limitations
    - bluez-peripheral's D-Bus ``ReadValue``/``WriteValue`` handlers are
      synchronous, so reads are served from values prefetched at startup and
      writes are dispatched as fire-and-forget tasks. Acknowledged writes are
      therefore acknowledged by the Pi, not by the PM5.
    - Adapter selection reaches into ``Adapter._proxy.path`` because
      bluez-peripheral exposes no public hciN accessor.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import sys
from collections.abc import Awaitable, Callable
from dataclasses import replace

from bleak import BleakClient, BleakScanner
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.gatt.characteristic import CharacteristicFlags as CharFlags
from bluez_peripheral.gatt.characteristic import characteristic
from bluez_peripheral.gatt.service import Service, ServiceCollection
from bluez_peripheral.util import Adapter, get_message_bus
from dbus_next import DBusError, Variant
from dbus_next.constants import PropertyAccess
from dbus_next.service import dbus_property

from concept2mqtt.ble import BleRelay, CharProperty, GattProfile, get_profile
from concept2mqtt.ble.profile import Service as ProfileService
from concept2mqtt.ble.profile import pm5_uuid


class _ServiceDataAdvertisement(Advertisement):
    """An ``Advertisement`` whose Service Data BlueZ will actually accept.

    bluez-peripheral declares ``LEAdvertisement1.ServiceData`` with D-Bus
    signature ``a{say}``; BlueZ requires ``a{sv}`` (each byte array wrapped in
    a variant) and rejects the whole advertisement with "Failed to parse
    advertisement" otherwise — an upstream bug.

    Unused by the default profile: hardware validation (2026-09-05) showed the
    Concept2 app discovers the relay from the ``ce060000`` UUID alone, and a
    legacy-advertising adapter has no room for Service Data beside a 128-bit
    UUID. Kept for profiles that do set ``advertised_service_data``.
    """

    @dbus_property(PropertyAccess.READ)
    def ServiceData(self) -> "a{sv}":  # noqa: F722  # dbus-next signature
        return {
            uuid: Variant("ay", bytes(data)) for uuid, data in self._serviceData.items()
        }


PM5_NAME_PREFIX = "PM5"
SCAN_TIMEOUT = 15.0
STATS_INTERVAL = 10.0
MODEL_NUMBER_UUID = pm5_uuid(0x0011)
SERIAL_NUMBER_UUID = pm5_uuid(0x0012)

_ADAPTER_INTERFACE = "org.bluez.Adapter1"
_ADVERT_MANAGER_INTERFACE = "org.bluez.LEAdvertisingManager1"
_OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
#: bluez-peripheral's default advertisement path, needed to unregister it.
_ADVERT_PATH = "/com/spacecheese/bluez_peripheral/advert0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("relay")


# ---------------------------------------------------------------------------
# Central side (bleak) — the real PM5
# ---------------------------------------------------------------------------
class BleakCentralLink:
    """Adapt a connected ``BleakClient`` to the relay's CentralLink protocol."""

    def __init__(self, client: BleakClient) -> None:
        self._client = client

    async def read(self, uuid: str) -> bytes:
        return bytes(await self._client.read_gatt_char(uuid))

    async def write(self, uuid: str, data: bytes, *, response: bool) -> None:
        await self._client.write_gatt_char(uuid, data, response=response)

    async def start_notify(
        self, uuid: str, callback: Callable[[str, bytes], Awaitable[None]]
    ) -> None:
        async def forward(_sender: object, data: bytearray) -> None:
            await callback(uuid, bytes(data))

        await self._client.start_notify(uuid, forward)

    async def stop_notify(self, uuid: str) -> None:
        await self._client.stop_notify(uuid)


# ---------------------------------------------------------------------------
# Peripheral side (bluez-peripheral) — the emulated PM5
# ---------------------------------------------------------------------------
_FLAGS = {
    CharProperty.READ: CharFlags.READ,
    CharProperty.WRITE: CharFlags.WRITE,
    CharProperty.WRITE_NO_RESPONSE: CharFlags.WRITE_WITHOUT_RESPONSE,
    CharProperty.NOTIFY: CharFlags.NOTIFY,
    CharProperty.INDICATE: CharFlags.INDICATE,
}


def _to_bluez_flags(properties: CharProperty) -> CharFlags:
    """Translate profile properties into BlueZ characteristic flags."""
    flags = CharFlags(0)
    for property_, flag in _FLAGS.items():
        if property_ in properties:
            flags |= flag
    return flags


class BluezPeripheralServer:
    """GATT server on a second adapter, built from a profile at runtime."""

    def __init__(self, adapter_name: str) -> None:
        self._adapter_name = adapter_name
        self._characteristics: dict[str, characteristic] = {}
        self._values: dict[str, bytes] = {}
        self._bus = None
        self._collection: ServiceCollection | None = None
        self._advert: Advertisement | None = None
        self._advert_manager = None

    async def start(
        self,
        profile: GattProfile,
        *,
        on_read: Callable[[str], Awaitable[bytes]],
        on_write: Callable[[str, bytes], Awaitable[None]],
    ) -> None:
        # D-Bus read handlers are synchronous, so every readable value has to
        # be resolved before the services are exported.
        for entry in profile:
            if entry.readable:
                self._values[entry.uuid] = await on_read(entry.uuid)

        self._bus = await get_message_bus()
        # Deliberately no pairing agent: a bonded consumer is the failure mode
        # this relay cannot recover from (see _make_non_bondable).
        adapter = await self._resolve_adapter()
        await self._reset_adapter(adapter)
        await self._make_non_bondable(adapter)
        await adapter.set_alias(profile.device_name)

        self._collection = ServiceCollection(
            [self._build_service(service, on_write) for service in profile.services]
        )
        await self._collection.register(self._bus, adapter=adapter)

        advert_cls = (
            _ServiceDataAdvertisement
            if profile.advertised_service_data
            else Advertisement
        )
        # Legacy advertising is 31 bytes; a 128-bit service UUID (18) plus
        # the full name overflows it and BlueZ rejects the whole advert.
        # The adapter alias (set above) still carries the full name over
        # GATT once connected.
        adv_name = profile.device_name.split()[0][:8]
        self._advert = advert_cls(
            adv_name,
            list(profile.advertised_service_uuids),
            0x0000,
            0,
            serviceData=dict(profile.advertised_service_data),
        )
        await self._advert.register(self._bus, adapter, path=_ADVERT_PATH)
        self._advert_manager = adapter._proxy.get_interface(_ADVERT_MANAGER_INTERFACE)
        log.info(
            "Advertising %r on %s as %s",
            profile.device_name,
            self._adapter_name,
            profile.name,
        )

    def _build_service(
        self,
        service_def: ProfileService,
        on_write: Callable[[str, bytes], Awaitable[None]],
    ) -> Service:
        service = Service(service_def.uuid, True)
        for entry in service_def.characteristics:
            char = characteristic(entry.uuid, _to_bluez_flags(entry.properties))
            char(
                self._make_getter(entry.uuid),
                self._make_setter(entry.uuid, on_write),
            )
            service.add_characteristic(char)
            self._characteristics[entry.uuid] = char
        return service

    def _make_getter(self, uuid: str) -> Callable[[object, object], bytes]:
        def getter(_service: object, _options: object) -> bytes:
            # Values are primed at startup, so this is the only place an
            # app-driven ReadValue is observable — the evidence for which
            # service the connecting app actually queries (Step B).
            log.debug("GATT read from consumer: %s", uuid)
            return self._values.get(uuid, b"")

        return getter

    def _make_setter(
        self, uuid: str, on_write: Callable[[str, bytes], Awaitable[None]]
    ) -> Callable[[object, bytes, object], None]:
        def setter(_service: object, data: bytes, _options: object) -> None:
            # Fire-and-forget: the D-Bus handler must not block the event loop.
            asyncio.get_running_loop().create_task(on_write(uuid, bytes(data)))

        return setter

    async def notify(self, uuid: str, data: bytes) -> None:
        self._characteristics[uuid].changed(data)

    async def stop(self) -> None:
        """Hand the advertisement and GATT application back to BlueZ.

        Both unregistrations must actually happen: BlueZ keeps a crashed
        relay's registrations, and the next RegisterAdvertisement then fails
        with "Failed to register advertisement" until the adapter is bounced.
        """
        if self._advert_manager is not None:
            try:
                await self._advert_manager.call_unregister_advertisement(_ADVERT_PATH)
            except Exception:
                log.warning("Could not unregister the advertisement", exc_info=True)
        if self._collection is not None:
            try:
                await self._collection.unregister()
            except Exception:
                log.warning("Could not unregister the GATT services", exc_info=True)
        if self._bus is not None:
            self._bus.disconnect()

    async def _reset_adapter(self, adapter: Adapter) -> None:
        """Power-cycle the adapter to drop registrations left by a crash.

        The scripted equivalent of ``hciconfig <hci> down && hciconfig <hci>
        up``, which the manual validation procedure needed before every
        restart.
        """
        await adapter.set_powered(False)
        await adapter.set_powered(True)

    async def _make_non_bondable(self, adapter: Adapter) -> None:
        """Refuse bonding, and forget any bond an earlier run stored.

        The emulated GATT database gets its attribute handles from BlueZ at
        registration time, so the layout can shift between runs. A bonded iOS
        client trusts its cached layout and skips re-discovery, and the
        connection then never completes — recoverable in the 2026-09-05 run
        only by wiping the bond on both sides. Not bonding at all keeps iOS
        re-discovering on every connect, and removes the pairing prompt the
        real PM5 does not show either. See R-PAIR-1 / R-GATT-STABLE-1.
        """
        interface = adapter._proxy.get_interface(_ADAPTER_INTERFACE)
        await interface.set_pairable(False)
        await interface.set_discoverable(False)

        adapter_path = adapter._proxy.path
        introspection = await self._bus.introspect("org.bluez", "/")
        root = self._bus.get_proxy_object("org.bluez", "/", introspection)
        objects = await root.get_interface(
            _OBJECT_MANAGER_INTERFACE
        ).call_get_managed_objects()
        for path in objects:
            if path.startswith(f"{adapter_path}/dev_"):
                log.info("Forgetting bonded device %s", path)
                with contextlib.suppress(DBusError):
                    await interface.call_remove_device(path)

    async def _resolve_adapter(self) -> Adapter:
        # Not Adapter.get_all(): it wraps every child node under /org/bluez
        # unconditionally, and this BlueZ build exposes a non-adapter
        # /org/bluez/test (SimAccessTest1) node that has no Adapter1
        # interface, crashing the enumeration before it reaches hci1.
        path = f"/org/bluez/{self._adapter_name}"
        try:
            introspection = await self._bus.introspect("org.bluez", path)
        except DBusError as exc:
            raise SystemExit(f"adapter {self._adapter_name} not found") from exc
        proxy = self._bus.get_proxy_object("org.bluez", path, introspection)
        return Adapter(proxy)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
async def _connect_pm5(adapter: str) -> BleakClient:
    """Scan for a PM5 on ``adapter`` and connect to it."""
    log.info("Scanning for a PM5 on %s (%ss)...", adapter, SCAN_TIMEOUT)
    device = await BleakScanner.find_device_by_filter(
        lambda d, _adv: bool(d.name and PM5_NAME_PREFIX in d.name),
        timeout=SCAN_TIMEOUT,
        adapter=adapter,
    )
    if device is None:
        raise SystemExit("No PM5 found — wake it with the handle and retry.")
    log.info("Found %s (%s); connecting...", device.name, device.address)
    client = BleakClient(device, adapter=adapter)
    await client.connect()
    return client


async def _identity(client: BleakClient, fallback: str) -> str:
    """Read the PM5's model and serial to mirror its advertised local name."""
    try:
        model = (await client.read_gatt_char(MODEL_NUMBER_UUID)).decode().strip("\x00")
        serial = (
            (await client.read_gatt_char(SERIAL_NUMBER_UUID)).decode().strip("\x00")
        )
    except Exception:
        log.warning("Could not read PM5 identity; advertising as %r", fallback)
        return fallback
    return f"{model} {serial} Row"


async def _report(relay: BleRelay) -> None:
    """Log relay counters periodically as evidence for the validation run."""
    while True:
        await asyncio.sleep(STATS_INTERVAL)
        log.info("%s", relay.stats)


async def run(central_adapter: str, peripheral_adapter: str, profile_name: str) -> None:
    """Connect to the PM5 and re-serve it until interrupted."""
    profile = get_profile(profile_name)
    client = await _connect_pm5(central_adapter)
    # Impersonate the real erg's advertised name so the app sees a familiar PM5.
    profile = replace(profile, device_name=await _identity(client, profile.device_name))
    relay = BleRelay(
        central=BleakCentralLink(client),
        peripheral=BluezPeripheralServer(peripheral_adapter),
        profile=profile,
    )
    reporter = asyncio.create_task(_report(relay))
    try:
        await relay.start()
        # The relay deliberately sets no sample-rate policy of its own: the
        # app writes ce060034 on every connect, and a relay-forced fast rate
        # is both overridden and (measured 2026-09-05) worse for latency on a
        # legacy-advertising link. See findings §11.1a / R-LATENCY-1.
        log.info("Relay live. Connect the Concept2 app to the advertised PM5.")
        await asyncio.Event().wait()
    finally:
        reporter.cancel()
        with contextlib.suppress(Exception):
            await relay.stop()
        await client.disconnect()
        log.info("Final counters: %s", relay.stats)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--central", default="hci0")
    parser.add_argument("--peripheral", default="hci1")
    parser.add_argument("--profile", default="pm5-proprietary")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Log every GATT read/write the connected app performs.",
    )
    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    try:
        asyncio.run(run(args.central, args.peripheral, args.profile))
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)


if __name__ == "__main__":
    main()
