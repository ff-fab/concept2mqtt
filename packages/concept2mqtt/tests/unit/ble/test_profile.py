"""Unit tests for concept2mqtt/ble/profile.py — GATT profile model and registry.

Test Techniques Used:
- Specification-based Testing: UUID expansion and profile lookup contracts
- Decision Table: CharProperty flag combinations → readable/writable/streaming
- Equivalence Partitioning: registered vs. unregistered profile names
- Error Guessing: unknown UUIDs and unknown profile names
"""

from __future__ import annotations

import pytest

from concept2mqtt.ble.errors import UnknownCharacteristicError, UnknownProfileError
from concept2mqtt.ble.profile import (
    DEFAULT_PROFILE_NAME,
    Characteristic,
    CharProperty,
    GattProfile,
    Service,
    get_profile,
    pm5_uuid,
    profile_names,
    sig_uuid,
)

# =============================================================================
# UUID helpers
# =============================================================================


class TestUuidExpansion:
    """16-bit suffixes expand to canonical lowercase 128-bit UUIDs.

    Technique: Specification-based Testing — UUID templates from ADR-003 and
    docs/planning/spec/csafe/ble_services.yaml.
    """

    def test_pm5_uuid_uses_concept2_base(self) -> None:
        assert pm5_uuid(0x0031) == "ce060031-43e5-11e4-916c-0800200c9a66"

    def test_pm5_uuid_lowercases_hex_digits(self) -> None:
        assert pm5_uuid(0x003A).startswith("ce06003a-")

    def test_sig_uuid_uses_bluetooth_base(self) -> None:
        assert sig_uuid(0x1826) == "00001826-0000-1000-8000-00805f9b34fb"


# =============================================================================
# Characteristic property flags
# =============================================================================


def _characteristic(properties: CharProperty) -> Characteristic:
    return Characteristic("uuid", "name", properties, 20)


class TestCharacteristicProperties:
    """Derived capability flags follow from the GATT property bits.

    Technique: Decision Table — property combination → derived capability.
    """

    @pytest.mark.parametrize(
        ("properties", "readable", "writable", "streaming"),
        [
            (CharProperty.READ, True, False, False),
            (CharProperty.WRITE, False, True, False),
            (CharProperty.WRITE_NO_RESPONSE, False, True, False),
            (CharProperty.NOTIFY, False, False, True),
            (CharProperty.INDICATE, False, False, True),
            (CharProperty.READ | CharProperty.WRITE, True, True, False),
        ],
    )
    def test_derived_capabilities(
        self,
        properties: CharProperty,
        readable: bool,
        writable: bool,
        streaming: bool,
    ) -> None:
        characteristic = _characteristic(properties)

        assert characteristic.readable is readable
        assert characteristic.writable is writable
        assert characteristic.streaming is streaming

    def test_write_with_response_true_for_acknowledged_write(self) -> None:
        assert _characteristic(CharProperty.WRITE).write_with_response is True

    def test_write_with_response_false_for_write_no_response(self) -> None:
        properties = CharProperty.WRITE_NO_RESPONSE
        assert _characteristic(properties).write_with_response is False


# =============================================================================
# Profile lookup
# =============================================================================


@pytest.fixture
def profile() -> GattProfile:
    """Two-characteristic profile with a single service."""
    return GattProfile(
        name="test",
        device_name="PM5",
        services=(
            Service(
                uuid="svc",
                name="Test Service",
                characteristics=(
                    _characteristic(CharProperty.READ),
                    Characteristic("other", "Other", CharProperty.NOTIFY, 20),
                ),
            ),
        ),
        advertised_service_uuids=("svc",),
    )


class TestGattProfileLookup:
    """Profiles expose their characteristics for lookup and iteration.

    Technique: Specification-based Testing — public API contract.
    """

    def test_iteration_yields_every_characteristic(self, profile: GattProfile) -> None:
        assert [c.uuid for c in profile] == ["uuid", "other"]

    def test_characteristic_lookup_returns_match(self, profile: GattProfile) -> None:
        assert profile.characteristic("other").name == "Other"

    def test_characteristic_lookup_is_case_insensitive(
        self, profile: GattProfile
    ) -> None:
        assert profile.characteristic("OTHER").uuid == "other"

    def test_characteristic_lookup_raises_for_unknown_uuid(
        self, profile: GattProfile
    ) -> None:
        with pytest.raises(UnknownCharacteristicError, match="missing"):
            profile.characteristic("missing")

    def test_service_uuids_preserve_declaration_order(
        self, profile: GattProfile
    ) -> None:
        assert profile.service_uuids == ("svc",)


# =============================================================================
# Registry
# =============================================================================


class TestProfileRegistry:
    """The registry is the swap point for the unresolved service question.

    Technique: Equivalence Partitioning — registered vs. unregistered names.
    """

    def test_registry_exposes_both_candidate_profiles(self) -> None:
        assert set(profile_names()) == {"pm5-proprietary", "ftms"}

    def test_default_is_the_proprietary_profile(self) -> None:
        assert get_profile().name == DEFAULT_PROFILE_NAME == "pm5-proprietary"

    def test_ftms_profile_advertises_fitness_machine_service(self) -> None:
        assert get_profile("ftms").advertised_service_uuids == (sig_uuid(0x1826),)

    def test_ftms_control_point_indicates_rather_than_notifies(self) -> None:
        control_point = get_profile("ftms").characteristic(sig_uuid(0x2AD9))

        assert control_point.streaming is True
        assert CharProperty.INDICATE in control_point.properties

    def test_unknown_name_raises_with_known_names_listed(self) -> None:
        with pytest.raises(UnknownProfileError, match="pm5-proprietary"):
            get_profile("nonexistent")

    def test_builders_return_independent_instances(self) -> None:
        assert get_profile() is not get_profile()


class TestPm5ProprietaryProfile:
    """The proprietary profile carries the identity and relay surfaces.

    Technique: Specification-based Testing — traceable to c2m-ooz.3 criteria.
    """

    def test_advertises_all_five_concept2_services(self) -> None:
        assert get_profile().service_uuids == (
            pm5_uuid(0x0010),
            pm5_uuid(0x0020),
            pm5_uuid(0x0030),
            pm5_uuid(0x0080),
            pm5_uuid(0x0040),
        )

    def test_advertises_only_the_rowing_service(self) -> None:
        """One 128-bit UUID is all a 31-byte advertising packet comfortably fits.

        Technique: Boundary Value Analysis — advertising payload limit.
        """
        advertised = get_profile().advertised_service_uuids

        assert advertised == (pm5_uuid(0x0030),)
        assert set(advertised) <= set(get_profile().service_uuids)

    def test_serial_number_is_readable_for_identity_emulation(self) -> None:
        serial = get_profile().characteristic(pm5_uuid(0x0012))

        assert serial.readable is True
        assert serial.max_length == 9

    def test_csafe_receive_accepts_acknowledged_writes(self) -> None:
        receive = get_profile().characteristic(pm5_uuid(0x0021))

        assert receive.write_with_response is True

    def test_csafe_transmit_notifies_beyond_the_spec_table(self) -> None:
        """CSAFE responses arrive as notifications; see SPEC_PROPERTY_ADDITIONS.

        Technique: Error Guessing — a read-only emulation would strand any
        app waiting on a CSAFE reply.
        """
        transmit = get_profile().characteristic(pm5_uuid(0x0022))

        assert transmit.readable is True
        assert transmit.streaming is True
