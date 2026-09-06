"""Conformance tests: pm5-proprietary profile vs. the CSAFE BLE spec YAML.

``docs/planning/spec/csafe/ble_services.yaml`` is the transcribed PM5 GATT
attribute table (Concept2 PM CSAFE Communication Definition Rev 0.25) and the
source of truth for what the emulated GATT server must expose. The profile in
``concept2mqtt/ble/profile.py`` restates it in Python so the package needs no
YAML parsing at runtime; these tests fail if the two ever drift.

Deliberate deviations are declared in ``profile.SPEC_PROPERTY_ADDITIONS`` and
are the only differences allowed.

Test Techniques Used:
- Specification-based Testing: every spec attribute is present and identical
- Round-trip Testing: spec YAML → profile → comparison against the spec
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from concept2mqtt.ble.profile import (
    SPEC_PROPERTY_ADDITIONS,
    CharProperty,
    pm5_proprietary_profile,
    pm5_uuid,
)

SPEC_PATH = (
    Path(__file__).resolve().parents[5]
    / "docs"
    / "planning"
    / "spec"
    / "csafe"
    / "ble_services.yaml"
)

_PERMISSION_TO_PROPERTY = {
    "READ": CharProperty.READ,
    "WRITE": CharProperty.WRITE,
    "NOTIFY": CharProperty.NOTIFY,
}


def _properties(permissions: list[str]) -> CharProperty:
    """Fold a spec permission list into a CharProperty flag."""
    folded = CharProperty(0)
    for permission in permissions:
        folded |= _PERMISSION_TO_PROPERTY[permission]
    return folded


def _spec_characteristics() -> dict[str, dict[str, Any]]:
    """Flatten the spec into ``{characteristic_uuid: attributes}``."""
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    flattened: dict[str, dict[str, Any]] = {}
    for service in spec["services"].values():
        for characteristic in service["characteristics"].values():
            uuid = pm5_uuid(int(characteristic["uuid_suffix"], 16))
            flattened[uuid] = {
                "name": characteristic["name"],
                "max_length": characteristic["bytes"],
                "properties": _properties(characteristic["permissions"])
                | SPEC_PROPERTY_ADDITIONS.get(uuid, CharProperty(0)),
            }
    return flattened


SPEC_CHARACTERISTICS = _spec_characteristics()


class TestServiceCoverage:
    """Every spec service is emulated, and nothing extra is invented."""

    def test_service_uuids_match_spec(self) -> None:
        spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
        expected = {
            pm5_uuid(int(service["uuid_suffix"], 16))
            for service in spec["services"].values()
        }

        assert set(pm5_proprietary_profile().service_uuids) == expected

    def test_characteristic_uuids_match_spec(self) -> None:
        actual = {characteristic.uuid for characteristic in pm5_proprietary_profile()}

        assert actual == set(SPEC_CHARACTERISTICS)


@pytest.mark.parametrize("uuid", sorted(SPEC_CHARACTERISTICS))
class TestCharacteristicConformance:
    """Each characteristic matches the spec's name, size and permissions.

    Technique: Specification-based Testing — one case per spec attribute.
    """

    def test_name_matches_spec(self, uuid: str) -> None:
        expected = SPEC_CHARACTERISTICS[uuid]["name"]

        assert pm5_proprietary_profile().characteristic(uuid).name == expected

    def test_max_length_matches_spec(self, uuid: str) -> None:
        expected = SPEC_CHARACTERISTICS[uuid]["max_length"]

        assert pm5_proprietary_profile().characteristic(uuid).max_length == expected

    def test_properties_match_spec_plus_declared_additions(self, uuid: str) -> None:
        expected = SPEC_CHARACTERISTICS[uuid]["properties"]

        assert pm5_proprietary_profile().characteristic(uuid).properties == expected


class TestDeclaredDeviations:
    """Deviations from the spec are explicit, not accidental.

    Technique: Error Guessing — an undocumented extra property is the exact
    kind of drift that makes the emulation diverge from the real PM5.
    """

    def test_only_the_csafe_transmit_characteristic_deviates(self) -> None:
        assert set(SPEC_PROPERTY_ADDITIONS) == {pm5_uuid(0x0022)}
