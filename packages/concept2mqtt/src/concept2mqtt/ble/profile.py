"""Declarative BLE GATT profiles used to emulate a PM5 on a peripheral adapter.

A profile is a pure data description of a GATT server: services, their
characteristics, and the properties each characteristic exposes. It carries no
transport code, so the same profile can drive a BlueZ D-Bus GATT server, a test
double, or documentation tooling.

Two profiles are registered:

``pm5-proprietary``
    Concept2's proprietary CSAFE-over-BLE services (``ce06xxxx`` UUID family),
    transcribed from ``docs/planning/spec/csafe/ble_services.yaml``.
``ftms``
    The standard Bluetooth SIG Fitness Machine Service (``0x1826``).

Which of the two the official Concept2 iPhone app actually queries is an open
question (ADR-003, issue c2m-ooz.3) that only a BLE traffic capture of a real
app session can settle. The registry below is the extension point: swap the
profile, keep the relay. See ``docs/testing/pm5-ble-relay-hardware-validation.md``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Flag, auto
from typing import Final

from concept2mqtt.ble.errors import UnknownCharacteristicError, UnknownProfileError

#: Concept2 proprietary 128-bit UUID template (``CE06XXXX-43E5-11E4-...``).
PM5_BASE_UUID: Final = "ce06{:04x}-43e5-11e4-916c-0800200c9a66"

#: Bluetooth SIG base UUID template for 16-bit assigned numbers.
SIG_BASE_UUID: Final = "0000{:04x}-0000-1000-8000-00805f9b34fb"


def pm5_uuid(suffix: int) -> str:
    """Expand a Concept2 16-bit UUID suffix to its full 128-bit form."""
    return PM5_BASE_UUID.format(suffix)


def sig_uuid(short: int) -> str:
    """Expand a Bluetooth SIG 16-bit assigned number to its 128-bit form."""
    return SIG_BASE_UUID.format(short)


class CharProperty(Flag):
    """GATT characteristic properties relevant to relaying."""

    READ = auto()
    WRITE = auto()
    WRITE_NO_RESPONSE = auto()
    NOTIFY = auto()
    INDICATE = auto()


_WRITABLE: Final = CharProperty.WRITE | CharProperty.WRITE_NO_RESPONSE
_STREAMING: Final = CharProperty.NOTIFY | CharProperty.INDICATE


@dataclass(frozen=True, slots=True)
class Characteristic:
    """A single GATT characteristic in an emulated profile."""

    uuid: str
    name: str
    properties: CharProperty
    max_length: int

    @property
    def readable(self) -> bool:
        """True when a central may read this characteristic."""
        return CharProperty.READ in self.properties

    @property
    def writable(self) -> bool:
        """True when a central may write this characteristic."""
        return bool(self.properties & _WRITABLE)

    @property
    def streaming(self) -> bool:
        """True when this characteristic pushes data (notify or indicate)."""
        return bool(self.properties & _STREAMING)

    @property
    def write_with_response(self) -> bool:
        """True when writes should use the acknowledged write procedure."""
        return CharProperty.WRITE in self.properties


@dataclass(frozen=True, slots=True)
class Service:
    """A GATT service and the characteristics it contains."""

    uuid: str
    name: str
    characteristics: tuple[Characteristic, ...]


@dataclass(frozen=True, slots=True)
class GattProfile:
    """A complete GATT server description plus its advertised identity.

    Attributes:
        name: Registry key for this profile.
        device_name: Local name to advertise, e.g. ``PM5 530426599 Row``.
        services: Every service the emulated GATT server exposes.
        advertised_service_uuids: The subset of ``services`` to put in the
            advertising packet. A BLE advertisement holds 31 bytes, so only one
            or two 128-bit UUIDs fit — advertise what consumers scan for.
    """

    name: str
    device_name: str
    services: tuple[Service, ...]
    advertised_service_uuids: tuple[str, ...]

    def __iter__(self) -> Iterator[Characteristic]:
        """Iterate every characteristic across every service."""
        for service in self.services:
            yield from service.characteristics

    def characteristic(self, uuid: str) -> Characteristic:
        """Look up a characteristic by UUID.

        Args:
            uuid: Full 128-bit UUID, case-insensitive.

        Returns:
            The matching characteristic.

        Raises:
            UnknownCharacteristicError: If no characteristic has that UUID.
        """
        wanted = uuid.lower()
        for characteristic in self:
            if characteristic.uuid == wanted:
                return characteristic
        raise UnknownCharacteristicError(uuid)

    @property
    def service_uuids(self) -> tuple[str, ...]:
        """UUIDs of all services, in declaration order."""
        return tuple(service.uuid for service in self.services)


# ---------------------------------------------------------------------------
# Profile tables
# ---------------------------------------------------------------------------

_READ: Final = CharProperty.READ
_WRITE: Final = CharProperty.WRITE
_NOTIFY: Final = CharProperty.NOTIFY
_READ_WRITE: Final = CharProperty.READ | CharProperty.WRITE

#: ``(uuid_suffix, name, properties, max_length)``.
CharacteristicRow = tuple[int, str, CharProperty, int]

#: ``(uuid_suffix, name, characteristics)``.
ServiceRow = tuple[int, str, tuple[CharacteristicRow, ...]]


def _build_services(
    rows: tuple[ServiceRow, ...], expand: Callable[[int], str]
) -> tuple[Service, ...]:
    """Turn declaration rows into services, expanding 16-bit UUID suffixes."""
    return tuple(
        Service(
            uuid=expand(suffix),
            name=name,
            characteristics=tuple(
                Characteristic(expand(c_suffix), c_name, properties, max_length)
                for c_suffix, c_name, properties, max_length in characteristics
            ),
        )
        for suffix, name, characteristics in rows
    )


# ---------------------------------------------------------------------------
# Concept2 proprietary profile (ce06xxxx)
# ---------------------------------------------------------------------------

#: Properties this profile grants beyond what ``ble_services.yaml`` lists.
#:
#: The spec's attribute table describes the PM Transmit characteristic as
#: read-only, but CSAFE responses are delivered as notifications on it in
#: practice, and open-source PM5 clients subscribe to it. Emulating it
#: read-only would strand any app waiting on a CSAFE reply, so the extra
#: property is granted deliberately. Confirm against the traffic capture
#: required by c2m-ooz.3.
SPEC_PROPERTY_ADDITIONS: Final[dict[str, CharProperty]] = {
    pm5_uuid(0x0022): CharProperty.NOTIFY,
}

_PM5_SERVICES: Final[tuple[ServiceRow, ...]] = (
    (
        0x0010,
        "C2 Device Information Service",
        (
            (0x0011, "Model Number String", _READ, 16),
            (0x0012, "Serial Number String", _READ, 9),
            (0x0013, "Hardware Revision String", _READ, 3),
            (0x0014, "Firmware Revision String", _READ, 20),
            (0x0015, "Manufacturer Name String", _READ, 16),
            (0x0016, "Erg Machine Type", _READ, 1),
            (0x0017, "ATT MTU", _READ, 2),
            (0x0018, "LL DLE", _READ, 2),
        ),
    ),
    (
        0x0020,
        "C2 PM Control Service",
        (
            (0x0021, "C2 PM Receive Characteristic", _WRITE, 20),
            (
                0x0022,
                "C2 PM Transmit Characteristic",
                _READ | SPEC_PROPERTY_ADDITIONS[pm5_uuid(0x0022)],
                20,
            ),
        ),
    ),
    (
        0x0030,
        "C2 Rowing Service",
        (
            (0x0031, "C2 Rowing General Status", _NOTIFY, 19),
            (0x0032, "C2 Rowing Additional Status 1", _NOTIFY, 17),
            (0x0033, "C2 Rowing Additional Status 2", _NOTIFY, 20),
            (
                0x0034,
                "C2 Rowing General Status and Additional Status Sample Rate",
                _READ_WRITE,
                1,
            ),
            (0x0035, "C2 Rowing Stroke Data", _NOTIFY, 20),
            (0x0036, "C2 Rowing Additional Stroke Data", _NOTIFY, 15),
            (0x0037, "C2 Rowing Split/Interval Data", _NOTIFY, 18),
            (0x0038, "C2 Rowing Additional Split/Interval Data", _NOTIFY, 19),
            (0x0039, "C2 Rowing End of Workout Summary Data", _NOTIFY, 20),
            (0x003A, "C2 Rowing End of Workout Additional Summary Data", _NOTIFY, 19),
            (0x003B, "C2 Rowing Heart Rate Belt Information", _NOTIFY, 6),
            (0x003C, "C2 Rowing End of Workout Additional Summary Data 2", _NOTIFY, 10),
            (0x003D, "C2 Force Curve Data", _NOTIFY, 288),
            (0x003E, "C2 Rowing Additional Status 3", _NOTIFY, 12),
            (0x003F, "C2 Rowing Logged Workout", _NOTIFY, 15),
        ),
    ),
    (
        0x0080,
        "C2 Multiplexed Information",
        ((0x0080, "C2 Multiplexed Information Characteristic", _NOTIFY, 20),),
    ),
    (
        0x0040,
        "C2 PM Heart Rate Service",
        ((0x0041, "C2 PM Heart Rate Receive Characteristic", _WRITE, 20),),
    ),
)


def pm5_proprietary_profile() -> GattProfile:
    """Build the Concept2 proprietary (``ce06xxxx``) PM5 profile.

    Transcribed from ``docs/planning/spec/csafe/ble_services.yaml``;
    ``tests/unit/ble/test_profile_spec_conformance.py`` fails if the two drift.
    """
    return GattProfile(
        name="pm5-proprietary",
        device_name="PM5",
        services=_build_services(_PM5_SERVICES, pm5_uuid),
        advertised_service_uuids=(pm5_uuid(0x0030),),
    )


# ---------------------------------------------------------------------------
# Standard Fitness Machine Service (0x1826)
# ---------------------------------------------------------------------------

_FTMS_SERVICES: Final[tuple[ServiceRow, ...]] = (
    (
        0x180A,
        "Device Information",
        (
            (0x2A24, "Model Number String", _READ, 16),
            (0x2A25, "Serial Number String", _READ, 16),
            (0x2A26, "Firmware Revision String", _READ, 20),
            (0x2A27, "Hardware Revision String", _READ, 16),
            (0x2A29, "Manufacturer Name String", _READ, 16),
        ),
    ),
    (
        0x1826,
        "Fitness Machine",
        (
            (0x2ACC, "Fitness Machine Feature", _READ, 8),
            (0x2AD1, "Rower Data", _NOTIFY, 20),
            (0x2AD3, "Training Status", _READ | _NOTIFY, 20),
            (
                0x2AD9,
                "Fitness Machine Control Point",
                _WRITE | CharProperty.INDICATE,
                20,
            ),
            (0x2ADA, "Fitness Machine Status", _NOTIFY, 20),
        ),
    ),
)


def ftms_profile() -> GattProfile:
    """Build the standard Fitness Machine Service profile for a rower.

    Warning:
        Unverified against real PM5 firmware. This is the Bluetooth SIG
        mandatory-for-rower attribute set, provided so the relay can be pointed
        at FTMS the moment the traffic capture required by c2m-ooz.3 shows the
        iPhone app uses it. Reconcile against a real ``bluetoothctl`` GATT dump
        of the PM5 before relying on it.
    """
    return GattProfile(
        name="ftms",
        device_name="PM5",
        services=_build_services(_FTMS_SERVICES, sig_uuid),
        advertised_service_uuids=(sig_uuid(0x1826),),
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_BUILDERS: Final = {
    "pm5-proprietary": pm5_proprietary_profile,
    "ftms": ftms_profile,
}

#: Default profile, per the working hypothesis recorded in ADR-003.
DEFAULT_PROFILE_NAME: Final = "pm5-proprietary"


def profile_names() -> tuple[str, ...]:
    """Names of every registered profile."""
    return tuple(_BUILDERS)


def get_profile(name: str = DEFAULT_PROFILE_NAME) -> GattProfile:
    """Build a registered profile by name.

    Args:
        name: One of :func:`profile_names`.

    Returns:
        A freshly built profile.

    Raises:
        UnknownProfileError: If ``name`` is not registered.
    """
    try:
        builder = _BUILDERS[name]
    except KeyError:
        raise UnknownProfileError(name, profile_names()) from None
    return builder()
