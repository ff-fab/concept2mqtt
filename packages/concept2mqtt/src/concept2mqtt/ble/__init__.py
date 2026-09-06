"""BLE peripheral relay: re-serve the PM5's single BLE connection.

See ADR-003 and issue c2m-ooz.3.
"""

from concept2mqtt.ble.errors import (
    BleRelayError,
    CharacteristicAccessError,
    UnknownCharacteristicError,
    UnknownProfileError,
)
from concept2mqtt.ble.profile import (
    DEFAULT_PROFILE_NAME,
    Characteristic,
    CharProperty,
    GattProfile,
    Service,
    ftms_profile,
    get_profile,
    pm5_proprietary_profile,
    pm5_uuid,
    profile_names,
    sig_uuid,
)
from concept2mqtt.ble.relay import (
    BleRelay,
    CentralLink,
    NotifyCallback,
    PeripheralServer,
    RelayStats,
)

__all__ = [
    "DEFAULT_PROFILE_NAME",
    "BleRelay",
    "BleRelayError",
    "CentralLink",
    "CharProperty",
    "Characteristic",
    "CharacteristicAccessError",
    "GattProfile",
    "NotifyCallback",
    "PeripheralServer",
    "RelayStats",
    "Service",
    "UnknownCharacteristicError",
    "UnknownProfileError",
    "ftms_profile",
    "get_profile",
    "pm5_proprietary_profile",
    "pm5_uuid",
    "profile_names",
    "sig_uuid",
]
