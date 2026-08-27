"""Exceptions raised by the BLE peripheral relay."""

from __future__ import annotations


class BleRelayError(Exception):
    """Base class for every BLE relay error."""


class UnknownProfileError(BleRelayError):
    """A GATT profile was requested by a name that is not registered."""

    def __init__(self, name: str, known: tuple[str, ...]) -> None:
        super().__init__(f"unknown GATT profile {name!r}; known: {', '.join(known)}")
        self.name = name
        self.known = known


class UnknownCharacteristicError(BleRelayError):
    """A characteristic UUID is not part of the active GATT profile."""

    def __init__(self, uuid: str) -> None:
        super().__init__(f"characteristic {uuid!r} is not in the active profile")
        self.uuid = uuid


class CharacteristicAccessError(BleRelayError):
    """A characteristic was accessed in a way its properties do not allow."""

    def __init__(self, uuid: str, operation: str) -> None:
        super().__init__(f"characteristic {uuid!r} does not support {operation}")
        self.uuid = uuid
        self.operation = operation
