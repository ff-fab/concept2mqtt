"""Python-side tests for CSAFE command type bindings.

Test Techniques Used:
- Specification-based Testing: enum values match CSAFE/PM5 spec
- Error Guessing: invalid values raise ValueError
- Equivalence Partitioning: representative coverage across enum types
"""

from __future__ import annotations

import csafe_codec
import pytest

# =============================================================================
# Enum name lookup — WorkoutType
# =============================================================================


class TestWorkoutTypeName:
    """workout_type_name converts u8 → variant name."""

    def test_just_row_no_splits(self) -> None:
        assert csafe_codec.workout_type_name(0) == "JustRowNoSplits"

    def test_fixed_time_interval(self) -> None:
        assert csafe_codec.workout_type_name(6) == "FixedTimeInterval"

    def test_fixed_calorie_interval(self) -> None:
        assert csafe_codec.workout_type_name(12) == "FixedCalorieInterval"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid WorkoutType"):
            csafe_codec.workout_type_name(99)


# =============================================================================
# Enum values dict — WorkoutType
# =============================================================================


class TestWorkoutTypeValues:
    """workout_type_values returns a complete dict."""

    def test_returns_dict(self) -> None:
        vals = csafe_codec.workout_type_values()
        assert isinstance(vals, dict)

    def test_has_expected_entries(self) -> None:
        vals = csafe_codec.workout_type_values()
        assert vals["JustRowNoSplits"] == 0
        assert vals["FixedDistInterval"] == 7
        assert vals["FixedCalorieInterval"] == 12

    def test_entry_count(self) -> None:
        assert len(csafe_codec.workout_type_values()) == 13


# =============================================================================
# Enum name lookup — IntervalType
# =============================================================================


class TestIntervalTypeName:
    """interval_type_name converts u8 → variant name."""

    def test_time(self) -> None:
        assert csafe_codec.interval_type_name(0) == "Time"

    def test_none_variant(self) -> None:
        assert csafe_codec.interval_type_name(255) == "None"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid IntervalType"):
            csafe_codec.interval_type_name(100)


class TestIntervalTypeValues:
    """interval_type_values returns a complete dict."""

    def test_entry_count(self) -> None:
        assert len(csafe_codec.interval_type_values()) == 11

    def test_has_none_at_255(self) -> None:
        assert csafe_codec.interval_type_values()["None"] == 255


# =============================================================================
# Enum name lookup — WorkoutState
# =============================================================================


class TestWorkoutStateName:
    """workout_state_name converts u8 → variant name."""

    def test_wait_to_begin(self) -> None:
        assert csafe_codec.workout_state_name(0) == "WaitToBegin"

    def test_workout_end(self) -> None:
        assert csafe_codec.workout_state_name(10) == "WorkoutEnd"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid WorkoutState"):
            csafe_codec.workout_state_name(50)


class TestWorkoutStateValues:
    """workout_state_values returns a complete dict."""

    def test_entry_count(self) -> None:
        assert len(csafe_codec.workout_state_values()) == 14


# =============================================================================
# Enum name lookup — ErgMachineType (complex enum, many variants)
# =============================================================================


class TestErgMachineTypeName:
    """erg_machine_type_name converts u8 → variant name."""

    def test_static_d(self) -> None:
        assert csafe_codec.erg_machine_type_name(0) == "StaticD"

    def test_bike(self) -> None:
        assert csafe_codec.erg_machine_type_name(192) == "Bike"

    def test_static_ski(self) -> None:
        assert csafe_codec.erg_machine_type_name(128) == "StaticSki"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid ErgMachineType"):
            csafe_codec.erg_machine_type_name(99)


class TestErgMachineTypeValues:
    """erg_machine_type_values returns a complete dict."""

    def test_entry_count(self) -> None:
        assert len(csafe_codec.erg_machine_type_values()) == 23

    def test_slides_d(self) -> None:
        assert csafe_codec.erg_machine_type_values()["SlidesD"] == 19


# =============================================================================
# Command ID constants — existence and values
# =============================================================================


class TestCommandIdConstants:
    """CMD_* constants are importable with correct values."""

    def test_get_status(self) -> None:
        assert csafe_codec.CMD_GET_STATUS == 0x80

    def test_reset(self) -> None:
        assert csafe_codec.CMD_RESET == 0x81

    def test_go_idle(self) -> None:
        assert csafe_codec.CMD_GO_IDLE == 0x82

    def test_get_version(self) -> None:
        assert csafe_codec.CMD_GET_VERSION == 0x91

    def test_get_serial(self) -> None:
        assert csafe_codec.CMD_GET_SERIAL == 0x94

    def test_get_calories(self) -> None:
        assert csafe_codec.CMD_GET_CALORIES == 0xA3

    def test_get_heart_rate(self) -> None:
        assert csafe_codec.CMD_GET_HEART_RATE == 0xB0

    def test_set_time(self) -> None:
        assert csafe_codec.CMD_SET_TIME == 0x11

    def test_set_program(self) -> None:
        assert csafe_codec.CMD_SET_PROGRAM == 0x24

    def test_get_caps(self) -> None:
        assert csafe_codec.CMD_GET_CAPS == 0x70


class TestWrapperCommandIdConstants:
    """PM wrapper CMD_* constants are importable with correct values."""

    def test_set_user_cfg1(self) -> None:
        assert csafe_codec.CMD_SET_USER_CFG1 == 0x1A

    def test_set_pm_cfg(self) -> None:
        assert csafe_codec.CMD_SET_PM_CFG == 0x76

    def test_set_pm_data(self) -> None:
        assert csafe_codec.CMD_SET_PM_DATA == 0x77

    def test_get_pm_cfg(self) -> None:
        assert csafe_codec.CMD_GET_PM_CFG == 0x7E

    def test_get_pm_data(self) -> None:
        assert csafe_codec.CMD_GET_PM_DATA == 0x7F
