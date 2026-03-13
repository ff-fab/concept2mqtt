"""Python-side tests for BLE notification decoder bindings.

Test Techniques Used:
- Specification-based Testing: byte payloads match PM5 BLE characteristic layouts
- Equivalence Partitioning: valid payloads, truncated payloads, edge values
- Error Guessing: empty data, short buffers, overflow cases
"""

from __future__ import annotations

import csafe_codec
import pytest

# =============================================================================
# 0x0031  General Status (19 bytes)
# =============================================================================


class TestDecodeGeneralStatus:
    """decode_general_status parses 19-byte General Status characteristic."""

    PAYLOAD = bytes(
        [
            0x10,
            0x27,
            0x00,  # elapsed_time_cs = 10000
            0xE8,
            0x03,
            0x00,  # distance_dm = 1000
            0x02,  # workout_type
            0x01,  # interval_type
            0x05,  # workout_state
            0x01,  # rowing_state
            0x02,  # stroke_state
            0xD0,
            0x07,
            0x00,  # total_work_distance_dm = 2000
            0x88,
            0x13,
            0x00,  # workout_duration = 5000
            0x00,  # workout_duration_type (time)
            0x78,  # drag_factor = 120
        ]
    )

    def test_decode_fields(self) -> None:
        gs = csafe_codec.decode_general_status(self.PAYLOAD)
        assert gs.elapsed_time_cs == 10000
        assert gs.distance_dm == 1000
        assert gs.workout_type == 2
        assert gs.interval_type == 1
        assert gs.workout_state == 5
        assert gs.rowing_state == 1
        assert gs.stroke_state == 2
        assert gs.total_work_distance_dm == 2000
        assert gs.workout_duration == 5000
        assert gs.workout_duration_type == 0
        assert gs.drag_factor == 120

    def test_returns_general_status_type(self) -> None:
        gs = csafe_codec.decode_general_status(self.PAYLOAD)
        assert isinstance(gs, csafe_codec.GeneralStatus)

    def test_repr(self) -> None:
        gs = csafe_codec.decode_general_status(self.PAYLOAD)
        r = repr(gs)
        assert "GeneralStatus(" in r
        assert "drag_factor=120" in r

    def test_equality(self) -> None:
        a = csafe_codec.decode_general_status(self.PAYLOAD)
        b = csafe_codec.decode_general_status(self.PAYLOAD)
        assert a == b

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 19 bytes"):
            csafe_codec.decode_general_status(bytes(18))

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 19 bytes"):
            csafe_codec.decode_general_status(b"")

    def test_extra_bytes_ignored(self) -> None:
        extended = self.PAYLOAD + bytes(5)
        gs = csafe_codec.decode_general_status(extended)
        assert gs.drag_factor == 120


# =============================================================================
# 0x0032  Additional Status 1 (17 bytes)
# =============================================================================


class TestDecodeAdditionalStatus1:
    """decode_additional_status_1 parses 17-byte Additional Status 1."""

    PAYLOAD = bytes(
        [
            0x10,
            0x27,
            0x00,  # elapsed_time_cs = 10000
            0xC8,
            0x00,  # speed_mms = 200
            0x1E,  # stroke_rate = 30
            0x8C,  # heartrate = 140
            0xF4,
            0x01,  # current_pace_cs = 500
            0xE8,
            0x03,  # average_pace_cs = 1000
            0x00,
            0x00,  # rest_distance = 0
            0x00,
            0x00,
            0x00,  # rest_time_cs = 0
            0x05,  # erg_machine_type = 5
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_additional_status_1(self.PAYLOAD)
        assert s.elapsed_time_cs == 10000
        assert s.speed_mms == 200
        assert s.stroke_rate == 30
        assert s.heartrate == 140
        assert s.current_pace_cs == 500
        assert s.average_pace_cs == 1000
        assert s.rest_distance == 0
        assert s.rest_time_cs == 0
        assert s.erg_machine_type == 5

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 17 bytes"):
            csafe_codec.decode_additional_status_1(bytes(16))


# =============================================================================
# 0x0033  Additional Status 2 (20 bytes)
# =============================================================================


class TestDecodeAdditionalStatus2:
    """decode_additional_status_2 parses 20-byte Additional Status 2."""

    PAYLOAD = bytes(
        [
            0x10,
            0x27,
            0x00,  # elapsed_time_cs = 10000
            0x03,  # interval_count = 3
            0xC8,
            0x00,  # average_power = 200
            0x64,
            0x00,  # total_calories = 100
            0xF4,
            0x01,  # split_avg_pace_cs = 500
            0x96,
            0x00,  # split_avg_power = 150
            0x2C,
            0x01,  # split_avg_calories = 300
            0x58,
            0x02,
            0x00,  # last_split_time_ds = 600
            0xE8,
            0x03,
            0x00,  # last_split_distance = 1000
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_additional_status_2(self.PAYLOAD)
        assert s.elapsed_time_cs == 10000
        assert s.interval_count == 3
        assert s.average_power == 200
        assert s.total_calories == 100
        assert s.split_avg_pace_cs == 500
        assert s.split_avg_power == 150
        assert s.split_avg_calories == 300
        assert s.last_split_time_ds == 600
        assert s.last_split_distance == 1000

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 20 bytes"):
            csafe_codec.decode_additional_status_2(bytes(19))


# =============================================================================
# 0x0035  Stroke Data (20 bytes)
# =============================================================================


class TestDecodeStrokeData:
    """decode_stroke_data parses 20-byte Stroke Data."""

    PAYLOAD = bytes(
        [
            0x10,
            0x27,
            0x00,  # elapsed_time_cs = 10000
            0xE8,
            0x03,
            0x00,  # distance_dm = 1000
            0x50,  # drive_length = 80
            0x28,  # drive_time = 40
            0xC8,
            0x00,  # stroke_recovery_time_cs = 200
            0x20,
            0x03,  # stroke_distance = 800
            0xF4,
            0x01,  # peak_drive_force = 500
            0x2C,
            0x01,  # average_drive_force = 300
            0x58,
            0x02,  # work_per_stroke = 600
            0x0A,
            0x00,  # stroke_count = 10
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_stroke_data(self.PAYLOAD)
        assert s.elapsed_time_cs == 10000
        assert s.distance_dm == 1000
        assert s.drive_length == 80
        assert s.drive_time == 40
        assert s.stroke_recovery_time_cs == 200
        assert s.stroke_distance == 800
        assert s.peak_drive_force == 500
        assert s.average_drive_force == 300
        assert s.work_per_stroke == 600
        assert s.stroke_count == 10

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 20 bytes"):
            csafe_codec.decode_stroke_data(bytes(19))


# =============================================================================
# 0x0036  Additional Stroke Data (15 bytes)
# =============================================================================


class TestDecodeAdditionalStrokeData:
    """decode_additional_stroke_data parses 15-byte Additional Stroke Data."""

    PAYLOAD = bytes(
        [
            0x10,
            0x27,
            0x00,  # elapsed_time_cs = 10000
            0xC8,
            0x00,  # stroke_power = 200
            0x2C,
            0x01,  # stroke_calories = 300
            0x0A,
            0x00,  # stroke_count = 10
            0x84,
            0x03,
            0x00,  # projected_work_time_s = 900
            0xD0,
            0x07,
            0x00,  # projected_work_distance = 2000
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_additional_stroke_data(self.PAYLOAD)
        assert s.elapsed_time_cs == 10000
        assert s.stroke_power == 200
        assert s.stroke_calories == 300
        assert s.stroke_count == 10
        assert s.projected_work_time_s == 900
        assert s.projected_work_distance == 2000

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 15 bytes"):
            csafe_codec.decode_additional_stroke_data(bytes(14))


# =============================================================================
# 0x0037  Split/Interval Data (18 bytes)
# =============================================================================


class TestDecodeSplitIntervalData:
    """decode_split_interval_data parses 18-byte Split/Interval Data."""

    PAYLOAD = bytes(
        [
            0x10,
            0x27,
            0x00,  # elapsed_time_cs = 10000
            0xE8,
            0x03,
            0x00,  # distance_dm = 1000
            0x58,
            0x02,
            0x00,  # split_interval_time_ds = 600
            0xF4,
            0x01,
            0x00,  # split_interval_distance = 500
            0x3C,
            0x00,  # interval_rest_time_s = 60
            0x00,
            0x00,  # interval_rest_distance = 0
            0x01,  # split_interval_type
            0x02,  # split_interval_number
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_split_interval_data(self.PAYLOAD)
        assert s.elapsed_time_cs == 10000
        assert s.distance_dm == 1000
        assert s.split_interval_time_ds == 600
        assert s.split_interval_distance == 500
        assert s.interval_rest_time_s == 60
        assert s.interval_rest_distance == 0
        assert s.split_interval_type == 1
        assert s.split_interval_number == 2

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 18 bytes"):
            csafe_codec.decode_split_interval_data(bytes(17))


# =============================================================================
# 0x0038  Additional Split/Interval Data (19 bytes)
# =============================================================================


class TestDecodeAdditionalSplitIntervalData:
    """decode_additional_split_interval_data parses 19 bytes."""

    PAYLOAD = bytes(
        [
            0x10,
            0x27,
            0x00,  # elapsed_time_cs = 10000
            0x1E,  # split_interval_avg_stroke_rate = 30
            0x8C,  # split_interval_work_heartrate = 140
            0x50,  # split_interval_rest_heartrate = 80
            0xF4,
            0x01,  # split_interval_avg_pace_ds = 500
            0x64,
            0x00,  # split_interval_total_calories = 100
            0x2C,
            0x01,  # split_interval_avg_calories = 300
            0xC8,
            0x00,  # split_interval_speed_mms = 200
            0x96,
            0x00,  # split_interval_power = 150
            0x78,  # split_avg_drag_factor = 120
            0x01,  # split_interval_number = 1
            0x05,  # erg_machine_type = 5
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_additional_split_interval_data(self.PAYLOAD)
        assert s.elapsed_time_cs == 10000
        assert s.split_interval_avg_stroke_rate == 30
        assert s.split_interval_work_heartrate == 140
        assert s.split_interval_rest_heartrate == 80
        assert s.split_interval_avg_pace_ds == 500
        assert s.split_interval_total_calories == 100
        assert s.split_interval_avg_calories == 300
        assert s.split_interval_speed_mms == 200
        assert s.split_interval_power == 150
        assert s.split_avg_drag_factor == 120
        assert s.split_interval_number == 1
        assert s.erg_machine_type == 5

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 19 bytes"):
            csafe_codec.decode_additional_split_interval_data(bytes(18))


# =============================================================================
# 0x0039  End of Workout Summary (20 bytes)
# =============================================================================


class TestDecodeEndOfWorkoutSummary:
    """decode_end_of_workout_summary parses 20 bytes."""

    PAYLOAD = bytes(
        [
            0x01,
            0x00,  # log_entry_date = 1
            0x02,
            0x00,  # log_entry_time = 2
            0x10,
            0x27,
            0x00,  # elapsed_time_cs = 10000
            0xE8,
            0x03,
            0x00,  # distance_dm = 1000
            0x1E,  # avg_stroke_rate = 30
            0x8C,  # ending_heartrate = 140
            0x82,  # avg_heartrate = 130
            0x50,  # min_heartrate = 80
            0xAA,  # max_heartrate = 170
            0x78,  # avg_drag_factor = 120
            0x64,  # recovery_heartrate = 100
            0x02,  # workout_type = 2
            0xF4,
            0x01,  # avg_pace_ds = 500
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_end_of_workout_summary(self.PAYLOAD)
        assert s.log_entry_date == 1
        assert s.log_entry_time == 2
        assert s.elapsed_time_cs == 10000
        assert s.distance_dm == 1000
        assert s.avg_stroke_rate == 30
        assert s.ending_heartrate == 140
        assert s.avg_heartrate == 130
        assert s.min_heartrate == 80
        assert s.max_heartrate == 170
        assert s.avg_drag_factor == 120
        assert s.recovery_heartrate == 100
        assert s.workout_type == 2
        assert s.avg_pace_ds == 500

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 20 bytes"):
            csafe_codec.decode_end_of_workout_summary(bytes(19))


# =============================================================================
# 0x003A  End of Workout Additional Summary (19 bytes)
# =============================================================================


class TestDecodeEndOfWorkoutAdditionalSummary:
    """decode_end_of_workout_additional_summary parses 19 bytes."""

    PAYLOAD = bytes(
        [
            0x01,
            0x00,  # log_entry_date = 1
            0x02,
            0x00,  # log_entry_time = 2
            0x01,  # split_interval_type = 1
            0xE8,
            0x03,  # split_interval_size = 1000
            0x05,  # split_interval_count = 5
            0x64,
            0x00,  # total_calories = 100
            0xC8,
            0x00,  # watts = 200
            0xD0,
            0x07,
            0x00,  # total_rest_distance = 2000
            0x3C,
            0x00,  # interval_rest_time_s = 60
            0x2C,
            0x01,  # avg_calories = 300
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_end_of_workout_additional_summary(self.PAYLOAD)
        assert s.log_entry_date == 1
        assert s.log_entry_time == 2
        assert s.split_interval_type == 1
        assert s.split_interval_size == 1000
        assert s.split_interval_count == 5
        assert s.total_calories == 100
        assert s.watts == 200
        assert s.total_rest_distance == 2000
        assert s.interval_rest_time_s == 60
        assert s.avg_calories == 300

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 19 bytes"):
            csafe_codec.decode_end_of_workout_additional_summary(bytes(18))


# =============================================================================
# 0x003B  Heart Rate Belt Information (6 bytes)
# =============================================================================


class TestDecodeHeartRateBeltInfo:
    """decode_heart_rate_belt_info parses 6-byte HR belt info."""

    PAYLOAD = bytes(
        [
            0x01,  # manufacturer_id = 1
            0x02,  # device_type = 2
            0x78,
            0x56,
            0x34,
            0x12,  # belt_id = 0x12345678
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_heart_rate_belt_info(self.PAYLOAD)
        assert s.manufacturer_id == 1
        assert s.device_type == 2
        assert s.belt_id == 0x12345678

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 6 bytes"):
            csafe_codec.decode_heart_rate_belt_info(bytes(5))


# =============================================================================
# 0x003C  End of Workout Additional Summary 2 (10 bytes)
# =============================================================================


class TestDecodeEndOfWorkoutAdditionalSummary2:
    """decode_end_of_workout_additional_summary_2 parses 10 bytes."""

    PAYLOAD = bytes(
        [
            0x01,
            0x00,  # log_entry_date = 1
            0x02,
            0x00,  # log_entry_time = 2
            0xF4,
            0x01,  # avg_pace_ds = 500
            0x03,  # game_identifier = 3
            0xE8,
            0x03,  # game_score = 1000
            0x05,  # erg_machine_type = 5
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_end_of_workout_additional_summary_2(self.PAYLOAD)
        assert s.log_entry_date == 1
        assert s.log_entry_time == 2
        assert s.avg_pace_ds == 500
        assert s.game_identifier == 3
        assert s.game_score == 1000
        assert s.erg_machine_type == 5

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 10 bytes"):
            csafe_codec.decode_end_of_workout_additional_summary_2(bytes(9))


# =============================================================================
# 0x003D  Force Curve Data (variable)
# =============================================================================


class TestDecodeForceCurveData:
    """decode_force_curve_data parses variable-length force curve."""

    def test_three_points(self) -> None:
        # header: total_notifications=2 (high nibble), point_count=3 (low nibble)
        payload = bytes(
            [
                0x23,  # (2 << 4) | 3
                0x01,  # sequence_number = 1
                0x64,
                0x00,  # data_point[0] = 100
                0xC8,
                0x00,  # data_point[1] = 200
                0x2C,
                0x01,  # data_point[2] = 300
            ]
        )
        fc = csafe_codec.decode_force_curve_data(payload)
        assert fc.total_notifications == 2
        assert fc.point_count == 3
        assert fc.sequence_number == 1
        assert fc.data_points == [100, 200, 300]

    def test_zero_points(self) -> None:
        payload = bytes([0x10, 0x00])  # 1 notification, 0 points, seq 0
        fc = csafe_codec.decode_force_curve_data(payload)
        assert fc.point_count == 0
        assert fc.data_points == []

    def test_signed_values(self) -> None:
        # -100 = 0xFF9C in little-endian: 0x9C, 0xFF
        payload = bytes([0x11, 0x00, 0x9C, 0xFF])
        fc = csafe_codec.decode_force_curve_data(payload)
        assert fc.data_points == [-100]

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError):
            csafe_codec.decode_force_curve_data(b"")

    def test_overflow_raises(self) -> None:
        # point_count = 10 exceeds max of 9
        with pytest.raises(ValueError, match="max is 9"):
            csafe_codec.decode_force_curve_data(bytes([0x1A, 0x00]))


# =============================================================================
# 0x003E  Additional Status 3 (12 bytes)
# =============================================================================


class TestDecodeAdditionalStatus3:
    """decode_additional_status_3 parses 12-byte Additional Status 3."""

    PAYLOAD = bytes(
        [
            0x01,  # operational_state = 1
            0x02,  # workout_verification_state = 2
            0x03,
            0x00,  # screen_number = 3
            0x00,
            0x00,  # last_error = 0
            0x00,  # calibration_mode = 0
            0x00,  # calibration_state = 0
            0x00,  # calibration_status = 0
            0x04,  # game_id = 4
            0xE8,
            0x03,  # game_score = 1000
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_additional_status_3(self.PAYLOAD)
        assert s.operational_state == 1
        assert s.workout_verification_state == 2
        assert s.screen_number == 3
        assert s.last_error == 0
        assert s.calibration_mode == 0
        assert s.calibration_state == 0
        assert s.calibration_status == 0
        assert s.game_id == 4
        assert s.game_score == 1000

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 12 bytes"):
            csafe_codec.decode_additional_status_3(bytes(11))


# =============================================================================
# 0x003F  Logged Workout (15 bytes)
# =============================================================================


class TestDecodeLoggedWorkout:
    """decode_logged_workout parses 15-byte Logged Workout."""

    PAYLOAD = bytes(
        [
            0x01,
            0x02,
            0x03,
            0x04,
            0x05,
            0x06,
            0x07,
            0x08,  # workout_hash (8 bytes LE)
            0x10,
            0x20,
            0x30,
            0x40,  # internal_log_address = 0x40302010
            0xE8,
            0x03,  # logged_workout_size = 1000
            0x05,  # erg_model_type = 5
        ]
    )

    def test_decode_fields(self) -> None:
        s = csafe_codec.decode_logged_workout(self.PAYLOAD)
        assert s.workout_hash == 0x0807060504030201
        assert s.internal_log_address == 0x40302010
        assert s.logged_workout_size == 1000
        assert s.erg_model_type == 5

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="expected 15 bytes"):
            csafe_codec.decode_logged_workout(bytes(14))


# =============================================================================
# 0x0080  Multiplexed dispatch
# =============================================================================


class TestDecodeMultiplexed:
    """decode_multiplexed dispatches on first byte and returns dict."""

    def test_general_status_via_mux(self) -> None:
        # 0x31 = GeneralStatus, then 19 bytes of payload
        payload = bytes([0x31]) + TestDecodeGeneralStatus.PAYLOAD
        result = csafe_codec.decode_multiplexed(payload)
        assert result["type"] == "GeneralStatus"
        assert isinstance(result["data"], csafe_codec.GeneralStatus)
        assert result["data"].drag_factor == 120

    def test_heart_rate_belt_via_mux(self) -> None:
        payload = bytes([0x3B]) + TestDecodeHeartRateBeltInfo.PAYLOAD
        result = csafe_codec.decode_multiplexed(payload)
        assert result["type"] == "HeartRateBeltInfo"
        assert result["data"].belt_id == 0x12345678

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            csafe_codec.decode_multiplexed(b"")

    def test_unknown_id_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown"):
            csafe_codec.decode_multiplexed(bytes([0xFF, 0x00]))

    def test_mux_layout_differs_raises(self) -> None:
        # 0x32 has a different mux layout
        with pytest.raises(ValueError, match="differs"):
            csafe_codec.decode_multiplexed(bytes([0x32]) + bytes(20))


# =============================================================================
# Response parser
# =============================================================================


class TestParseStatusByte:
    """parse_status_byte extracts toggle, prev_frame_status, server_state."""

    def test_idle_ok(self) -> None:
        # bit 7=0, bits 5-4=00 (Ok), bits 3-0=0x02 (Idle)
        sb = csafe_codec.parse_status_byte(0x02)
        assert sb.frame_toggle is False
        assert sb.prev_frame_status == "Ok"
        assert sb.server_state == "Idle"

    def test_toggle_in_use(self) -> None:
        # bit 7=1, bits 5-4=00 (Ok), bits 3-0=0x05 (InUse)
        sb = csafe_codec.parse_status_byte(0x85)
        assert sb.frame_toggle is True
        assert sb.server_state == "InUse"

    def test_reject_ready(self) -> None:
        # bit 7=0, bits 5-4=01 (Reject), bits 3-0=0x01 (Ready)
        sb = csafe_codec.parse_status_byte(0x11)
        assert sb.prev_frame_status == "Reject"
        assert sb.server_state == "Ready"

    def test_invalid_state_raises(self) -> None:
        # bits 3-0 = 0x04 is not a valid server state
        with pytest.raises(ValueError, match="invalid server state"):
            csafe_codec.parse_status_byte(0x04)

    def test_returns_status_byte_type(self) -> None:
        sb = csafe_codec.parse_status_byte(0x02)
        assert isinstance(sb, csafe_codec.StatusByte)

    def test_repr(self) -> None:
        sb = csafe_codec.parse_status_byte(0x02)
        r = repr(sb)
        assert "StatusByte(" in r
        assert "Idle" in r

    def test_equality(self) -> None:
        a = csafe_codec.parse_status_byte(0x02)
        b = csafe_codec.parse_status_byte(0x02)
        assert a == b


class TestParseCommandResponses:
    """parse_command_responses extracts command blocks from raw data."""

    def test_single_command(self) -> None:
        # cmd_id=0x80, byte_count=2, data=[0x01, 0x02]
        data = bytes([0x80, 0x02, 0x01, 0x02])
        responses = csafe_codec.parse_command_responses(data)
        assert len(responses) == 1
        assert responses[0].command_id == 0x80
        assert responses[0].data == b"\x01\x02"

    def test_multiple_commands(self) -> None:
        # Two commands
        data = bytes([0x80, 0x01, 0xAA, 0x81, 0x02, 0xBB, 0xCC])
        responses = csafe_codec.parse_command_responses(data)
        assert len(responses) == 2
        assert responses[0].command_id == 0x80
        assert responses[0].data == b"\xaa"
        assert responses[1].command_id == 0x81
        assert responses[1].data == b"\xbb\xcc"

    def test_empty_data(self) -> None:
        responses = csafe_codec.parse_command_responses(b"")
        assert responses == []

    def test_zero_length_command(self) -> None:
        data = bytes([0x80, 0x00])
        responses = csafe_codec.parse_command_responses(data)
        assert len(responses) == 1
        assert responses[0].data == b""

    def test_truncated_raises(self) -> None:
        with pytest.raises(ValueError, match="truncated"):
            csafe_codec.parse_command_responses(bytes([0x80]))

    def test_insufficient_data_raises(self) -> None:
        with pytest.raises(ValueError, match="0x80"):
            csafe_codec.parse_command_responses(bytes([0x80, 0x05, 0x01]))

    def test_returns_command_response_type(self) -> None:
        responses = csafe_codec.parse_command_responses(bytes([0x80, 0x01, 0x00]))
        assert isinstance(responses[0], csafe_codec.CommandResponse)


class TestParseResponse:
    """parse_response parses status byte + command blocks."""

    def test_status_only(self) -> None:
        # status byte = 0x02 (Idle, Ok, no toggle), no commands
        resp = csafe_codec.parse_response(bytes([0x02]))
        assert resp.status.server_state == "Idle"
        assert resp.commands == []

    def test_status_with_commands(self) -> None:
        # status=0x01 (Ready), then cmd 0x80 with 1 byte of data
        resp = csafe_codec.parse_response(bytes([0x01, 0x80, 0x01, 0xFF]))
        assert resp.status.server_state == "Ready"
        assert len(resp.commands) == 1
        assert resp.commands[0].command_id == 0x80
        assert resp.commands[0].data == b"\xff"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            csafe_codec.parse_response(b"")

    def test_returns_response_type(self) -> None:
        resp = csafe_codec.parse_response(bytes([0x02]))
        assert isinstance(resp, csafe_codec.Response)

    def test_repr(self) -> None:
        resp = csafe_codec.parse_response(bytes([0x02]))
        r = repr(resp)
        assert "Response(" in r
        assert "Idle" in r
