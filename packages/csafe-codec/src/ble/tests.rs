use super::*;

// ── Helper ────────────────────────────────────────────────────────────

/// Verify that decoding a too-short slice returns InsufficientBytes.
fn assert_too_short<T: std::fmt::Debug>(
    decoder: fn(&[u8]) -> Result<T, BleDecodeError>,
    expected_len: usize,
) {
    let short = vec![0u8; expected_len - 1];
    let err = decoder(&short).unwrap_err();
    assert_eq!(
        err,
        BleDecodeError::InsufficientBytes {
            expected: expected_len,
            actual: expected_len - 1,
        }
    );
}

// ── General Status (0x0031, 19 bytes) ─────────────────────────────────

#[test]
fn general_status_decodes_all_zeros() {
    let data = [0u8; 19];
    let gs = decode_general_status(&data).unwrap();
    assert_eq!(gs.elapsed_time_cs, 0);
    assert_eq!(gs.distance_dm, 0);
    assert_eq!(gs.workout_type, 0);
    assert_eq!(gs.drag_factor, 0);
}

#[test]
fn general_status_assembles_multibyte_fields() {
    // elapsed_time = 0x030201 = 197121 centiseconds
    // distance     = 0x060504 = 394500 decimetres
    let mut data = [0u8; 19];
    data[0] = 0x01;
    data[1] = 0x02;
    data[2] = 0x03;
    data[3] = 0x04;
    data[4] = 0x05;
    data[5] = 0x06;
    data[6] = 0x0A; // workout_type
    data[7] = 0x0B; // interval_type
    data[8] = 0x0C; // workout_state
    data[9] = 0x0D; // rowing_state
    data[10] = 0x0E; // stroke_state
    data[11] = 0x10;
    data[12] = 0x20;
    data[13] = 0x30; // total_work_distance = 0x302010
    data[14] = 0xAA;
    data[15] = 0xBB;
    data[16] = 0xCC; // workout_duration = 0xCCBBAA
    data[17] = 0x01; // duration_type
    data[18] = 0x7F; // drag_factor

    let gs = decode_general_status(&data).unwrap();
    assert_eq!(gs.elapsed_time_cs, 0x030201);
    assert_eq!(gs.distance_dm, 0x060504);
    assert_eq!(gs.workout_type, 0x0A);
    assert_eq!(gs.interval_type, 0x0B);
    assert_eq!(gs.workout_state, 0x0C);
    assert_eq!(gs.rowing_state, 0x0D);
    assert_eq!(gs.stroke_state, 0x0E);
    assert_eq!(gs.total_work_distance_dm, 0x302010);
    assert_eq!(gs.workout_duration, 0xCCBBAA);
    assert_eq!(gs.workout_duration_type, 1);
    assert_eq!(gs.drag_factor, 0x7F);
}

#[test]
fn general_status_too_short() {
    assert_too_short(decode_general_status, 19);
}

#[test]
fn general_status_extra_bytes_ignored() {
    let data = [0u8; 25];
    assert!(decode_general_status(&data).is_ok());
}

// ── Additional Status 1 (0x0032, 17 bytes) ────────────────────────────

#[test]
fn additional_status_1_round_trip() {
    let mut data = [0u8; 17];
    data[0] = 0x10;
    data[1] = 0x27;
    data[2] = 0x00; // elapsed_time = 10000 cs = 100 s
    data[3] = 0xE8;
    data[4] = 0x03; // speed = 1000 = 1.000 m/s
    data[5] = 28; // stroke_rate
    data[6] = 155; // heartrate
    data[7] = 0xC4;
    data[8] = 0x09; // current_pace = 2500 cs = 25 s / 500m
    data[9] = 0xD0;
    data[10] = 0x07; // average_pace = 2000 cs
    data[11] = 0x00;
    data[12] = 0x00; // rest_distance = 0
    data[13] = 0x00;
    data[14] = 0x00;
    data[15] = 0x00; // rest_time = 0
    data[16] = 0x05; // erg_machine_type

    let s = decode_additional_status_1(&data).unwrap();
    assert_eq!(s.elapsed_time_cs, 10000);
    assert_eq!(s.speed_mms, 1000);
    assert_eq!(s.stroke_rate, 28);
    assert_eq!(s.heartrate, 155);
    assert_eq!(s.current_pace_cs, 2500);
    assert_eq!(s.average_pace_cs, 2000);
    assert_eq!(s.rest_distance, 0);
    assert_eq!(s.rest_time_cs, 0);
    assert_eq!(s.erg_machine_type, 5);
}

#[test]
fn additional_status_1_too_short() {
    assert_too_short(decode_additional_status_1, 17);
}

// ── Additional Status 2 (0x0033, 20 bytes) ────────────────────────────

#[test]
fn additional_status_2_round_trip() {
    let mut data = [0u8; 20];
    data[3] = 3; // interval_count
    data[4] = 0x50;
    data[5] = 0x00; // average_power = 80 W
    data[6] = 0xF4;
    data[7] = 0x01; // total_calories = 500
    data[14] = 0x58;
    data[15] = 0x02;
    data[16] = 0x00; // last_split_time = 600 ds = 60 s
    data[17] = 0xD0;
    data[18] = 0x07;
    data[19] = 0x00; // last_split_distance = 2000 m

    let s = decode_additional_status_2(&data).unwrap();
    assert_eq!(s.interval_count, 3);
    assert_eq!(s.average_power, 80);
    assert_eq!(s.total_calories, 500);
    assert_eq!(s.last_split_time_ds, 600);
    assert_eq!(s.last_split_distance, 2000);
}

#[test]
fn additional_status_2_too_short() {
    assert_too_short(decode_additional_status_2, 20);
}

// ── Stroke Data (0x0035, 20 bytes) ────────────────────────────────────

#[test]
fn stroke_data_round_trip() {
    let mut data = [0u8; 20];
    data[6] = 120; // drive_length = 1.20 m
    data[7] = 85; // drive_time = 0.85 s
    data[8] = 0xC8;
    data[9] = 0x00; // recovery_time = 200 cs = 2.00 s
    data[10] = 0x80;
    data[11] = 0x03; // stroke_distance = 896 = 8.96 m
    data[12] = 0x20;
    data[13] = 0x03; // peak_drive_force = 800 = 80.0 lbs
    data[14] = 0x00;
    data[15] = 0x02; // avg_drive_force = 512 = 51.2 lbs
    data[16] = 0xBC;
    data[17] = 0x02; // work_per_stroke = 700 = 70.0 J
    data[18] = 0x64;
    data[19] = 0x00; // stroke_count = 100

    let s = decode_stroke_data(&data).unwrap();
    assert_eq!(s.drive_length, 120);
    assert_eq!(s.drive_time, 85);
    assert_eq!(s.stroke_recovery_time_cs, 200);
    assert_eq!(s.stroke_distance, 896);
    assert_eq!(s.peak_drive_force, 800);
    assert_eq!(s.average_drive_force, 512);
    assert_eq!(s.work_per_stroke, 700);
    assert_eq!(s.stroke_count, 100);
}

#[test]
fn stroke_data_too_short() {
    assert_too_short(decode_stroke_data, 20);
}

// ── Additional Stroke Data (0x0036, 15 bytes) ─────────────────────────

#[test]
fn additional_stroke_data_round_trip() {
    let mut data = [0u8; 15];
    data[3] = 0x50;
    data[4] = 0x00; // stroke_power = 80 W
    data[5] = 0xE8;
    data[6] = 0x03; // stroke_calories = 1000 cal/hr
    data[7] = 0x0A;
    data[8] = 0x00; // stroke_count = 10
    data[9] = 0x2C;
    data[10] = 0x01;
    data[11] = 0x00; // projected_work_time = 300 s
    data[12] = 0xD0;
    data[13] = 0x07;
    data[14] = 0x00; // projected_work_distance = 2000 m

    let s = decode_additional_stroke_data(&data).unwrap();
    assert_eq!(s.stroke_power, 80);
    assert_eq!(s.stroke_calories, 1000);
    assert_eq!(s.stroke_count, 10);
    assert_eq!(s.projected_work_time_s, 300);
    assert_eq!(s.projected_work_distance, 2000);
}

#[test]
fn additional_stroke_data_too_short() {
    assert_too_short(decode_additional_stroke_data, 15);
}

// ── Split/Interval Data (0x0037, 18 bytes) ────────────────────────────

#[test]
fn split_interval_data_round_trip() {
    let mut data = [0u8; 18];
    data[6] = 0xE8;
    data[7] = 0x03;
    data[8] = 0x00; // split_interval_time = 1000 ds = 100 s
    data[9] = 0xD0;
    data[10] = 0x07;
    data[11] = 0x00; // split_interval_distance = 2000 m
    data[12] = 0x3C;
    data[13] = 0x00; // interval_rest_time = 60 s
    data[14] = 0x00;
    data[15] = 0x00; // interval_rest_distance = 0
    data[16] = 0x02; // split_interval_type
    data[17] = 0x01; // split_interval_number

    let s = decode_split_interval_data(&data).unwrap();
    assert_eq!(s.split_interval_time_ds, 1000);
    assert_eq!(s.split_interval_distance, 2000);
    assert_eq!(s.interval_rest_time_s, 60);
    assert_eq!(s.interval_rest_distance, 0);
    assert_eq!(s.split_interval_type, 2);
    assert_eq!(s.split_interval_number, 1);
}

#[test]
fn split_interval_data_too_short() {
    assert_too_short(decode_split_interval_data, 18);
}

// ── Additional Split/Interval Data (0x0038, 19 bytes) ─────────────────

#[test]
fn additional_split_interval_data_round_trip() {
    let mut data = [0u8; 19];
    data[3] = 28; // avg_stroke_rate
    data[4] = 150; // work_heartrate
    data[5] = 100; // rest_heartrate
    data[6] = 0xC4;
    data[7] = 0x09; // avg_pace = 2500 ds
    data[16] = 110; // drag_factor
    data[17] = 3; // split_interval_number
    data[18] = 5; // erg_machine_type

    let s = decode_additional_split_interval_data(&data).unwrap();
    assert_eq!(s.split_interval_avg_stroke_rate, 28);
    assert_eq!(s.split_interval_work_heartrate, 150);
    assert_eq!(s.split_interval_rest_heartrate, 100);
    assert_eq!(s.split_interval_avg_pace_ds, 2500);
    assert_eq!(s.split_avg_drag_factor, 110);
    assert_eq!(s.split_interval_number, 3);
    assert_eq!(s.erg_machine_type, 5);
}

#[test]
fn additional_split_interval_data_too_short() {
    assert_too_short(decode_additional_split_interval_data, 19);
}

// ── End of Workout Summary (0x0039, 20 bytes) ─────────────────────────

#[test]
fn end_of_workout_summary_round_trip() {
    let mut data = [0u8; 20];
    data[0] = 0x01;
    data[1] = 0x00; // log_entry_date = 1
    data[2] = 0x02;
    data[3] = 0x00; // log_entry_time = 2
    data[10] = 28; // avg_stroke_rate
    data[11] = 180; // ending_heartrate
    data[12] = 155; // avg_heartrate
    data[13] = 120; // min_heartrate
    data[14] = 185; // max_heartrate
    data[15] = 110; // avg_drag_factor
    data[16] = 0; // recovery_heartrate (not yet available)
    data[17] = 0x01; // workout_type
    data[18] = 0xE8;
    data[19] = 0x03; // avg_pace = 1000 ds = 100 s / 500m

    let s = decode_end_of_workout_summary(&data).unwrap();
    assert_eq!(s.log_entry_date, 1);
    assert_eq!(s.log_entry_time, 2);
    assert_eq!(s.avg_stroke_rate, 28);
    assert_eq!(s.ending_heartrate, 180);
    assert_eq!(s.avg_heartrate, 155);
    assert_eq!(s.min_heartrate, 120);
    assert_eq!(s.max_heartrate, 185);
    assert_eq!(s.avg_drag_factor, 110);
    assert_eq!(s.recovery_heartrate, 0);
    assert_eq!(s.workout_type, 1);
    assert_eq!(s.avg_pace_ds, 1000);
}

#[test]
fn end_of_workout_summary_too_short() {
    assert_too_short(decode_end_of_workout_summary, 20);
}

// ── End of Workout Additional Summary (0x003A, 19 bytes) ──────────────

#[test]
fn end_of_workout_additional_summary_round_trip() {
    let mut data = [0u8; 19];
    data[4] = 0x03; // split_interval_type
    data[5] = 0xD0;
    data[6] = 0x07; // split_interval_size = 2000
    data[7] = 5; // split_interval_count
    data[8] = 0xF4;
    data[9] = 0x01; // total_calories = 500
    data[10] = 0x50;
    data[11] = 0x00; // watts = 80
    data[15] = 0x3C;
    data[16] = 0x00; // interval_rest_time = 60 s
    data[17] = 0xE8;
    data[18] = 0x03; // avg_calories = 1000 cal/hr

    let s = decode_end_of_workout_additional_summary(&data).unwrap();
    assert_eq!(s.split_interval_type, 3);
    assert_eq!(s.split_interval_size, 2000);
    assert_eq!(s.split_interval_count, 5);
    assert_eq!(s.total_calories, 500);
    assert_eq!(s.watts, 80);
    assert_eq!(s.interval_rest_time_s, 60);
    assert_eq!(s.avg_calories, 1000);
}

#[test]
fn end_of_workout_additional_summary_too_short() {
    assert_too_short(decode_end_of_workout_additional_summary, 19);
}

// ── Heart Rate Belt Information (0x003B, 6 bytes) ─────────────────────

#[test]
fn heart_rate_belt_info_round_trip() {
    let data = [0x01, 0x02, 0x78, 0x56, 0x34, 0x12];
    let s = decode_heart_rate_belt_info(&data).unwrap();
    assert_eq!(s.manufacturer_id, 1);
    assert_eq!(s.device_type, 2);
    assert_eq!(s.belt_id, 0x12345678);
}

#[test]
fn heart_rate_belt_info_too_short() {
    assert_too_short(decode_heart_rate_belt_info, 6);
}

// ── End of Workout Additional Summary 2 (0x003C, 10 bytes) ───────────

#[test]
fn end_of_workout_additional_summary_2_round_trip() {
    let mut data = [0u8; 10];
    data[4] = 0xC8;
    data[5] = 0x00; // avg_pace = 200 ds = 20 s / 500m
    data[6] = 0x03; // game_identifier
    data[7] = 0xFF;
    data[8] = 0x00; // game_score = 255
    data[9] = 0x05; // erg_machine_type

    let s = decode_end_of_workout_additional_summary_2(&data).unwrap();
    assert_eq!(s.avg_pace_ds, 200);
    assert_eq!(s.game_identifier, 3);
    assert_eq!(s.game_score, 255);
    assert_eq!(s.erg_machine_type, 5);
}

#[test]
fn end_of_workout_additional_summary_2_too_short() {
    assert_too_short(decode_end_of_workout_additional_summary_2, 10);
}

// ── Force Curve Data (0x003D, variable) ───────────────────────────────

#[test]
fn force_curve_data_three_points() {
    // header: total_notifications=2 (MS nibble), point_count=3 (LS nibble)
    // sequence_number=0
    // 3 signed 16-bit points: 100, -50, 200
    let data = [
        0x23, // header: 2 total, 3 points
        0x00, // sequence
        0x64, 0x00, // 100
        0xCE, 0xFF, // -50 (two's complement)
        0xC8, 0x00, // 200
    ];
    let fc = decode_force_curve_data(&data).unwrap();
    assert_eq!(fc.total_notifications, 2);
    assert_eq!(fc.point_count, 3);
    assert_eq!(fc.sequence_number, 0);
    assert_eq!(fc.data_points, vec![100, -50, 200]);
}

#[test]
fn force_curve_data_zero_points() {
    let data = [0x10, 0x00]; // 1 total notification, 0 points
    let fc = decode_force_curve_data(&data).unwrap();
    assert_eq!(fc.total_notifications, 1);
    assert_eq!(fc.point_count, 0);
    assert!(fc.data_points.is_empty());
}

#[test]
fn force_curve_data_overflow() {
    // header claims 10 points (> 9 max)
    let data = [0x1A, 0x00];
    let err = decode_force_curve_data(&data).unwrap_err();
    assert_eq!(
        err,
        BleDecodeError::ForceCurveOverflow {
            claimed_points: 10,
            max_points: 9,
        }
    );
}

#[test]
fn force_curve_data_too_short_for_header() {
    assert_too_short(decode_force_curve_data, 2);
}

#[test]
fn force_curve_data_too_short_for_points() {
    // Claims 2 points (4 bytes) but only has 2 bytes of point data
    let data = [0x12, 0x00, 0x01, 0x00];
    let err = decode_force_curve_data(&data).unwrap_err();
    assert_eq!(
        err,
        BleDecodeError::InsufficientBytes {
            expected: 6,
            actual: 4,
        }
    );
}

// ── Additional Status 3 (0x003E, 12 bytes) ────────────────────────────

#[test]
fn additional_status_3_round_trip() {
    let mut data = [0u8; 12];
    data[0] = 0x01; // operational_state
    data[1] = 0x02; // workout_verification_state
    data[2] = 0x05;
    data[3] = 0x00; // screen_number = 5
    data[4] = 0x10;
    data[5] = 0x00; // last_error = 16
    data[6] = 0x00; // calibration_mode
    data[7] = 0x00; // calibration_state
    data[8] = 0x00; // calibration_status
    data[9] = 0x03; // game_id
    data[10] = 0x64;
    data[11] = 0x00; // game_score = 100

    let s = decode_additional_status_3(&data).unwrap();
    assert_eq!(s.operational_state, 1);
    assert_eq!(s.workout_verification_state, 2);
    assert_eq!(s.screen_number, 5);
    assert_eq!(s.last_error, 16);
    assert_eq!(s.game_id, 3);
    assert_eq!(s.game_score, 100);
}

#[test]
fn additional_status_3_too_short() {
    assert_too_short(decode_additional_status_3, 12);
}

// ── Logged Workout (0x003F, 15 bytes) ─────────────────────────────────

#[test]
fn logged_workout_round_trip() {
    let mut data = [0u8; 15];
    // workout_hash = 0x0807060504030201
    data[0] = 0x01;
    data[1] = 0x02;
    data[2] = 0x03;
    data[3] = 0x04;
    data[4] = 0x05;
    data[5] = 0x06;
    data[6] = 0x07;
    data[7] = 0x08;
    // internal_log_address = 0x0C0B0A09
    data[8] = 0x09;
    data[9] = 0x0A;
    data[10] = 0x0B;
    data[11] = 0x0C;
    // logged_workout_size = 0x0E0D
    data[12] = 0x0D;
    data[13] = 0x0E;
    data[14] = 0x05; // erg_model_type

    let s = decode_logged_workout(&data).unwrap();
    assert_eq!(s.workout_hash, 0x0807060504030201);
    assert_eq!(s.internal_log_address, 0x0C0B0A09);
    assert_eq!(s.logged_workout_size, 0x0E0D);
    assert_eq!(s.erg_model_type, 5);
}

#[test]
fn logged_workout_too_short() {
    assert_too_short(decode_logged_workout, 15);
}

// ── Multiplexed dispatch (0x0080) ─────────────────────────────────────

#[test]
fn multiplexed_general_status() {
    let mut data = vec![0x31]; // characteristic ID
    data.extend_from_slice(&[0u8; 19]); // 19 bytes of general status
    let result = decode_multiplexed(&data).unwrap();
    assert!(matches!(result, RowingCharacteristic::GeneralStatus(_)));
}

#[test]
fn multiplexed_heart_rate_belt() {
    let data = [0x3B, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06];
    let result = decode_multiplexed(&data).unwrap();
    match result {
        RowingCharacteristic::HeartRateBeltInfo(info) => {
            assert_eq!(info.manufacturer_id, 1);
            assert_eq!(info.device_type, 2);
        }
        other => panic!("expected HeartRateBeltInfo, got {other:?}"),
    }
}

#[test]
fn multiplexed_unknown_id() {
    let data = [0xFF, 0x00];
    let err = decode_multiplexed(&data).unwrap_err();
    assert_eq!(err, MultiplexedError::UnknownId { id: 0xFF });
}

#[test]
fn multiplexed_empty() {
    let err = decode_multiplexed(&[]).unwrap_err();
    assert_eq!(err, MultiplexedError::Empty);
}

#[test]
fn multiplexed_decode_error_propagated() {
    // ID 0x31 (general_status) but payload too short
    let data = [0x31, 0x00, 0x00];
    let err = decode_multiplexed(&data).unwrap_err();
    assert!(matches!(err, MultiplexedError::Decode(_)));
}
