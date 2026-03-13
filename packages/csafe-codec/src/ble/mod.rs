//! BLE notification decoders for PM5 rowing characteristics.
//!
//! Each characteristic from the Rowing Service (UUID suffix 0x0031–0x003F)
//! has a fixed-layout binary format described in `ble_services.yaml`.
//! This module provides typed structs and `decode_*` functions that parse
//! raw notification bytes into structured data.
//!
//! All multi-byte integer fields are assembled from individual bytes
//! (little-endian order) into their natural integer type.  Values are
//! kept in their raw protocol units (e.g. centiseconds, tenths of metres)
//! — no floating-point conversion is performed here.

use std::fmt;

// ── Error type ────────────────────────────────────────────────────────

/// Errors that can occur while decoding a BLE notification.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BleDecodeError {
    /// The notification payload is shorter than expected.
    InsufficientBytes { expected: usize, actual: usize },
    /// The force-curve header claims more data points than the payload
    /// can hold.
    ForceCurveOverflow { claimed_points: u8, max_points: u8 },
}

impl fmt::Display for BleDecodeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InsufficientBytes { expected, actual } => {
                write!(
                    f,
                    "BLE notification too short: expected {expected} bytes, got {actual}"
                )
            }
            Self::ForceCurveOverflow {
                claimed_points,
                max_points,
            } => {
                write!(
                    f,
                    "force curve header claims {claimed_points} data points, max is {max_points}"
                )
            }
        }
    }
}

impl std::error::Error for BleDecodeError {}

// ── Helpers ───────────────────────────────────────────────────────────

/// Assemble a 24-bit unsigned integer from three little-endian bytes.
#[inline]
fn u24(lo: u8, mid: u8, hi: u8) -> u32 {
    u32::from(lo) | (u32::from(mid) << 8) | (u32::from(hi) << 16)
}

/// Assemble a 16-bit unsigned integer from two little-endian bytes.
#[inline]
fn u16le(lo: u8, hi: u8) -> u16 {
    u16::from(lo) | (u16::from(hi) << 8)
}

/// Assemble a signed 16-bit integer from two little-endian bytes.
#[inline]
fn i16le(lo: u8, hi: u8) -> i16 {
    i16::from_le_bytes([lo, hi])
}

/// Check that `data` has at least `expected` bytes.
#[inline]
fn check_len(data: &[u8], expected: usize) -> Result<(), BleDecodeError> {
    if data.len() < expected {
        Err(BleDecodeError::InsufficientBytes {
            expected,
            actual: data.len(),
        })
    } else {
        Ok(())
    }
}

// ── 0x0031  General Status (19 bytes) ─────────────────────────────────

/// Decoded C2 Rowing General Status characteristic (UUID suffix 0x0031).
///
/// Notification rate controlled by the sample-rate characteristic (0x0034).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GeneralStatus {
    /// Elapsed time in 0.01 s (24-bit).
    pub elapsed_time_cs: u32,
    /// Distance in 0.1 m (24-bit).
    pub distance_dm: u32,
    pub workout_type: u8,
    pub interval_type: u8,
    pub workout_state: u8,
    pub rowing_state: u8,
    pub stroke_state: u8,
    /// Total work distance in 0.1 m (24-bit).
    pub total_work_distance_dm: u32,
    /// Workout duration (24-bit).  Interpretation depends on
    /// `workout_duration_type` (time in 0.01 s or distance).
    pub workout_duration: u32,
    /// 0 = time, 1 = distance.
    pub workout_duration_type: u8,
    pub drag_factor: u8,
}

/// Decode a General Status notification (19 bytes).
pub fn decode_general_status(data: &[u8]) -> Result<GeneralStatus, BleDecodeError> {
    check_len(data, 19)?;
    Ok(GeneralStatus {
        elapsed_time_cs: u24(data[0], data[1], data[2]),
        distance_dm: u24(data[3], data[4], data[5]),
        workout_type: data[6],
        interval_type: data[7],
        workout_state: data[8],
        rowing_state: data[9],
        stroke_state: data[10],
        total_work_distance_dm: u24(data[11], data[12], data[13]),
        workout_duration: u24(data[14], data[15], data[16]),
        workout_duration_type: data[17],
        drag_factor: data[18],
    })
}

// ── 0x0032  Additional Status 1 (17 bytes) ────────────────────────────

/// Decoded C2 Rowing Additional Status 1 (UUID suffix 0x0032).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdditionalStatus1 {
    /// Elapsed time in 0.01 s (24-bit).
    pub elapsed_time_cs: u32,
    /// Speed in 0.001 m/s (16-bit).
    pub speed_mms: u16,
    /// Stroke rate in strokes/min.
    pub stroke_rate: u8,
    /// Heart rate in bpm (255 = invalid).
    pub heartrate: u8,
    /// Current pace in 0.01 s per 500 m (16-bit).
    pub current_pace_cs: u16,
    /// Average pace in 0.01 s per 500 m (16-bit).
    pub average_pace_cs: u16,
    /// Rest distance in metres (16-bit).
    pub rest_distance: u16,
    /// Rest time in 0.01 s (24-bit).
    pub rest_time_cs: u32,
    pub erg_machine_type: u8,
}

/// Decode an Additional Status 1 notification (17 bytes).
pub fn decode_additional_status_1(data: &[u8]) -> Result<AdditionalStatus1, BleDecodeError> {
    check_len(data, 17)?;
    Ok(AdditionalStatus1 {
        elapsed_time_cs: u24(data[0], data[1], data[2]),
        speed_mms: u16le(data[3], data[4]),
        stroke_rate: data[5],
        heartrate: data[6],
        current_pace_cs: u16le(data[7], data[8]),
        average_pace_cs: u16le(data[9], data[10]),
        rest_distance: u16le(data[11], data[12]),
        rest_time_cs: u24(data[13], data[14], data[15]),
        erg_machine_type: data[16],
    })
}

// ── 0x0033  Additional Status 2 (20 bytes) ────────────────────────────

/// Decoded C2 Rowing Additional Status 2 (UUID suffix 0x0033).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdditionalStatus2 {
    /// Elapsed time in 0.01 s (24-bit).
    pub elapsed_time_cs: u32,
    pub interval_count: u8,
    /// Average power in watts (16-bit).
    pub average_power: u16,
    /// Total calories (16-bit).
    pub total_calories: u16,
    /// Split/interval average pace in 0.01 s per 500 m (16-bit).
    pub split_avg_pace_cs: u16,
    /// Split/interval average power in watts (16-bit).
    pub split_avg_power: u16,
    /// Split/interval average calories in cals/hr (16-bit).
    pub split_avg_calories: u16,
    /// Last split time in 0.1 s (24-bit).
    pub last_split_time_ds: u32,
    /// Last split distance in metres (24-bit).
    pub last_split_distance: u32,
}

/// Decode an Additional Status 2 notification (20 bytes).
pub fn decode_additional_status_2(data: &[u8]) -> Result<AdditionalStatus2, BleDecodeError> {
    check_len(data, 20)?;
    Ok(AdditionalStatus2 {
        elapsed_time_cs: u24(data[0], data[1], data[2]),
        interval_count: data[3],
        average_power: u16le(data[4], data[5]),
        total_calories: u16le(data[6], data[7]),
        split_avg_pace_cs: u16le(data[8], data[9]),
        split_avg_power: u16le(data[10], data[11]),
        split_avg_calories: u16le(data[12], data[13]),
        last_split_time_ds: u24(data[14], data[15], data[16]),
        last_split_distance: u24(data[17], data[18], data[19]),
    })
}

// ── 0x0035  Stroke Data (20 bytes) ────────────────────────────────────

/// Decoded C2 Rowing Stroke Data (UUID suffix 0x0035).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StrokeData {
    /// Elapsed time in 0.01 s (24-bit).
    pub elapsed_time_cs: u32,
    /// Distance in 0.1 m (24-bit).
    pub distance_dm: u32,
    /// Drive length in 0.01 m.
    pub drive_length: u8,
    /// Drive time in 0.01 s.
    pub drive_time: u8,
    /// Stroke recovery time in 0.01 s (16-bit).
    pub stroke_recovery_time_cs: u16,
    /// Stroke distance in 0.01 m (16-bit).
    pub stroke_distance: u16,
    /// Peak drive force in 0.1 lbs (16-bit).
    pub peak_drive_force: u16,
    /// Average drive force in 0.1 lbs (16-bit).
    pub average_drive_force: u16,
    /// Work per stroke in 0.1 J (16-bit).
    pub work_per_stroke: u16,
    /// Stroke count (16-bit).
    pub stroke_count: u16,
}

/// Decode a Stroke Data notification (20 bytes).
pub fn decode_stroke_data(data: &[u8]) -> Result<StrokeData, BleDecodeError> {
    check_len(data, 20)?;
    Ok(StrokeData {
        elapsed_time_cs: u24(data[0], data[1], data[2]),
        distance_dm: u24(data[3], data[4], data[5]),
        drive_length: data[6],
        drive_time: data[7],
        stroke_recovery_time_cs: u16le(data[8], data[9]),
        stroke_distance: u16le(data[10], data[11]),
        peak_drive_force: u16le(data[12], data[13]),
        average_drive_force: u16le(data[14], data[15]),
        work_per_stroke: u16le(data[16], data[17]),
        stroke_count: u16le(data[18], data[19]),
    })
}

// ── 0x0036  Additional Stroke Data (15 bytes) ─────────────────────────

/// Decoded C2 Rowing Additional Stroke Data (UUID suffix 0x0036).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdditionalStrokeData {
    /// Elapsed time in 0.01 s (24-bit).
    pub elapsed_time_cs: u32,
    /// Stroke power in watts (16-bit).
    pub stroke_power: u16,
    /// Stroke caloric burn rate in cal/hr (16-bit).
    pub stroke_calories: u16,
    /// Stroke count (16-bit).
    pub stroke_count: u16,
    /// Projected work time in seconds (24-bit).
    pub projected_work_time_s: u32,
    /// Projected work distance in metres (24-bit).
    pub projected_work_distance: u32,
}

/// Decode an Additional Stroke Data notification (15 bytes).
pub fn decode_additional_stroke_data(data: &[u8]) -> Result<AdditionalStrokeData, BleDecodeError> {
    check_len(data, 15)?;
    Ok(AdditionalStrokeData {
        elapsed_time_cs: u24(data[0], data[1], data[2]),
        stroke_power: u16le(data[3], data[4]),
        stroke_calories: u16le(data[5], data[6]),
        stroke_count: u16le(data[7], data[8]),
        projected_work_time_s: u24(data[9], data[10], data[11]),
        projected_work_distance: u24(data[12], data[13], data[14]),
    })
}

// ── 0x0037  Split/Interval Data (18 bytes) ────────────────────────────

/// Decoded C2 Rowing Split/Interval Data (UUID suffix 0x0037).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SplitIntervalData {
    /// Elapsed time in 0.01 s (24-bit).
    pub elapsed_time_cs: u32,
    /// Distance in 0.1 m (24-bit).
    pub distance_dm: u32,
    /// Split/interval time in 0.1 s (24-bit).
    pub split_interval_time_ds: u32,
    /// Split/interval distance in metres (24-bit).
    pub split_interval_distance: u32,
    /// Interval rest time in seconds (16-bit).
    pub interval_rest_time_s: u16,
    /// Interval rest distance in metres (16-bit).
    pub interval_rest_distance: u16,
    pub split_interval_type: u8,
    pub split_interval_number: u8,
}

/// Decode a Split/Interval Data notification (18 bytes).
pub fn decode_split_interval_data(data: &[u8]) -> Result<SplitIntervalData, BleDecodeError> {
    check_len(data, 18)?;
    Ok(SplitIntervalData {
        elapsed_time_cs: u24(data[0], data[1], data[2]),
        distance_dm: u24(data[3], data[4], data[5]),
        split_interval_time_ds: u24(data[6], data[7], data[8]),
        split_interval_distance: u24(data[9], data[10], data[11]),
        interval_rest_time_s: u16le(data[12], data[13]),
        interval_rest_distance: u16le(data[14], data[15]),
        split_interval_type: data[16],
        split_interval_number: data[17],
    })
}

// ── 0x0038  Additional Split/Interval Data (19 bytes) ─────────────────

/// Decoded C2 Rowing Additional Split/Interval Data (UUID suffix 0x0038).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdditionalSplitIntervalData {
    /// Elapsed time in 0.01 s (24-bit).
    pub elapsed_time_cs: u32,
    /// Average stroke rate in strokes/min.
    pub split_interval_avg_stroke_rate: u8,
    /// Work heart rate in bpm.
    pub split_interval_work_heartrate: u8,
    /// Rest heart rate in bpm.
    pub split_interval_rest_heartrate: u8,
    /// Average pace in 0.1 s per 500 m (16-bit).
    pub split_interval_avg_pace_ds: u16,
    /// Total calories (16-bit).
    pub split_interval_total_calories: u16,
    /// Average calories in cals/hr (16-bit).
    pub split_interval_avg_calories: u16,
    /// Speed in 0.001 m/s (16-bit).
    pub split_interval_speed_mms: u16,
    /// Power in watts (16-bit).
    pub split_interval_power: u16,
    pub split_avg_drag_factor: u8,
    pub split_interval_number: u8,
    pub erg_machine_type: u8,
}

/// Decode an Additional Split/Interval Data notification (19 bytes).
pub fn decode_additional_split_interval_data(
    data: &[u8],
) -> Result<AdditionalSplitIntervalData, BleDecodeError> {
    check_len(data, 19)?;
    Ok(AdditionalSplitIntervalData {
        elapsed_time_cs: u24(data[0], data[1], data[2]),
        split_interval_avg_stroke_rate: data[3],
        split_interval_work_heartrate: data[4],
        split_interval_rest_heartrate: data[5],
        split_interval_avg_pace_ds: u16le(data[6], data[7]),
        split_interval_total_calories: u16le(data[8], data[9]),
        split_interval_avg_calories: u16le(data[10], data[11]),
        split_interval_speed_mms: u16le(data[12], data[13]),
        split_interval_power: u16le(data[14], data[15]),
        split_avg_drag_factor: data[16],
        split_interval_number: data[17],
        erg_machine_type: data[18],
    })
}

// ── 0x0039  End of Workout Summary (20 bytes) ─────────────────────────

/// Decoded C2 Rowing End of Workout Summary (UUID suffix 0x0039).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EndOfWorkoutSummary {
    /// Log entry date (16-bit).
    pub log_entry_date: u16,
    /// Log entry time (16-bit).
    pub log_entry_time: u16,
    /// Elapsed time in 0.01 s (24-bit).
    pub elapsed_time_cs: u32,
    /// Distance in 0.1 m (24-bit).
    pub distance_dm: u32,
    /// Average stroke rate in strokes/min.
    pub avg_stroke_rate: u8,
    /// Ending heart rate in bpm.
    pub ending_heartrate: u8,
    /// Average heart rate in bpm.
    pub avg_heartrate: u8,
    /// Minimum heart rate in bpm.
    pub min_heartrate: u8,
    /// Maximum heart rate in bpm.
    pub max_heartrate: u8,
    pub avg_drag_factor: u8,
    /// Recovery heart rate in bpm (0 until valid).
    pub recovery_heartrate: u8,
    pub workout_type: u8,
    /// Average pace in 0.1 s per 500 m (16-bit).
    pub avg_pace_ds: u16,
}

/// Decode an End of Workout Summary notification (20 bytes).
pub fn decode_end_of_workout_summary(data: &[u8]) -> Result<EndOfWorkoutSummary, BleDecodeError> {
    check_len(data, 20)?;
    Ok(EndOfWorkoutSummary {
        log_entry_date: u16le(data[0], data[1]),
        log_entry_time: u16le(data[2], data[3]),
        elapsed_time_cs: u24(data[4], data[5], data[6]),
        distance_dm: u24(data[7], data[8], data[9]),
        avg_stroke_rate: data[10],
        ending_heartrate: data[11],
        avg_heartrate: data[12],
        min_heartrate: data[13],
        max_heartrate: data[14],
        avg_drag_factor: data[15],
        recovery_heartrate: data[16],
        workout_type: data[17],
        avg_pace_ds: u16le(data[18], data[19]),
    })
}

// ── 0x003A  End of Workout Additional Summary (19 bytes) ──────────────

/// Decoded C2 Rowing End of Workout Additional Summary (UUID suffix 0x003A).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EndOfWorkoutAdditionalSummary {
    /// Log entry date (16-bit).
    pub log_entry_date: u16,
    /// Log entry time (16-bit).
    pub log_entry_time: u16,
    pub split_interval_type: u8,
    /// Split/interval size in metres or seconds (16-bit).
    pub split_interval_size: u16,
    pub split_interval_count: u8,
    /// Total calories (16-bit).
    pub total_calories: u16,
    /// Watts (16-bit).
    pub watts: u16,
    /// Total rest distance in metres (24-bit).
    pub total_rest_distance: u32,
    /// Interval rest time in seconds (16-bit).
    pub interval_rest_time_s: u16,
    /// Average calories in cals/hr (16-bit).
    pub avg_calories: u16,
}

/// Decode an End of Workout Additional Summary notification (19 bytes).
pub fn decode_end_of_workout_additional_summary(
    data: &[u8],
) -> Result<EndOfWorkoutAdditionalSummary, BleDecodeError> {
    check_len(data, 19)?;
    Ok(EndOfWorkoutAdditionalSummary {
        log_entry_date: u16le(data[0], data[1]),
        log_entry_time: u16le(data[2], data[3]),
        split_interval_type: data[4],
        split_interval_size: u16le(data[5], data[6]),
        split_interval_count: data[7],
        total_calories: u16le(data[8], data[9]),
        watts: u16le(data[10], data[11]),
        total_rest_distance: u24(data[12], data[13], data[14]),
        interval_rest_time_s: u16le(data[15], data[16]),
        avg_calories: u16le(data[17], data[18]),
    })
}

// ── 0x003B  Heart Rate Belt Information (6 bytes) ─────────────────────

/// Decoded C2 Rowing Heart Rate Belt Information (UUID suffix 0x003B).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HeartRateBeltInfo {
    pub manufacturer_id: u8,
    pub device_type: u8,
    /// Belt ID (32-bit, assembled from 4 bytes).
    pub belt_id: u32,
}

/// Decode a Heart Rate Belt Information notification (6 bytes).
pub fn decode_heart_rate_belt_info(data: &[u8]) -> Result<HeartRateBeltInfo, BleDecodeError> {
    check_len(data, 6)?;
    Ok(HeartRateBeltInfo {
        manufacturer_id: data[0],
        device_type: data[1],
        belt_id: u32::from(data[2])
            | (u32::from(data[3]) << 8)
            | (u32::from(data[4]) << 16)
            | (u32::from(data[5]) << 24),
    })
}

// ── 0x003C  End of Workout Additional Summary 2 (10 bytes) ───────────

/// Decoded C2 Rowing End of Workout Additional Summary 2 (UUID suffix 0x003C).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EndOfWorkoutAdditionalSummary2 {
    /// Log entry date (16-bit).
    pub log_entry_date: u16,
    /// Log entry time (16-bit).
    pub log_entry_time: u16,
    /// Average pace in 0.1 s per 500 m (16-bit).
    pub avg_pace_ds: u16,
    pub game_identifier: u8,
    /// Game score (16-bit).
    pub game_score: u16,
    pub erg_machine_type: u8,
}

/// Decode an End of Workout Additional Summary 2 notification (10 bytes).
pub fn decode_end_of_workout_additional_summary_2(
    data: &[u8],
) -> Result<EndOfWorkoutAdditionalSummary2, BleDecodeError> {
    check_len(data, 10)?;
    Ok(EndOfWorkoutAdditionalSummary2 {
        log_entry_date: u16le(data[0], data[1]),
        log_entry_time: u16le(data[2], data[3]),
        avg_pace_ds: u16le(data[4], data[5]),
        game_identifier: data[6],
        game_score: u16le(data[7], data[8]),
        erg_machine_type: data[9],
    })
}

// ── 0x003D  Force Curve Data (variable, 2–20 bytes per notification) ──

/// Decoded C2 Force Curve Data notification (UUID suffix 0x003D).
///
/// Force curve data is sent across multiple successive notifications.
/// Each notification carries a header describing the total notification
/// count and the number of data points in *this* notification.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ForceCurveData {
    /// Total number of notifications for this force curve.
    pub total_notifications: u8,
    /// Number of 16-bit data points in this notification.
    pub point_count: u8,
    /// Sequence number for ordering the notifications.
    pub sequence_number: u8,
    /// The force curve data points (signed 16-bit values).
    pub data_points: Vec<i16>,
}

/// Decode a Force Curve Data notification (variable length, min 2 bytes).
pub fn decode_force_curve_data(data: &[u8]) -> Result<ForceCurveData, BleDecodeError> {
    check_len(data, 2)?;

    let header = data[0];
    let total_notifications = header >> 4;
    let point_count = header & 0x0F;
    let sequence_number = data[1];

    // Each data point is 2 bytes; max 9 points per notification.
    if point_count > 9 {
        return Err(BleDecodeError::ForceCurveOverflow {
            claimed_points: point_count,
            max_points: 9,
        });
    }

    let required = 2 + (point_count as usize) * 2;
    check_len(data, required)?;

    let mut data_points = Vec::with_capacity(point_count as usize);
    for i in 0..point_count as usize {
        let offset = 2 + i * 2;
        data_points.push(i16le(data[offset], data[offset + 1]));
    }

    Ok(ForceCurveData {
        total_notifications,
        point_count,
        sequence_number,
        data_points,
    })
}

// ── 0x003E  Additional Status 3 (12 bytes) ────────────────────────────

/// Decoded C2 Rowing Additional Status 3 (UUID suffix 0x003E).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdditionalStatus3 {
    pub operational_state: u8,
    pub workout_verification_state: u8,
    /// Screen number (16-bit).
    pub screen_number: u16,
    /// Last error code (16-bit).
    pub last_error: u16,
    /// Calibration mode (BikeErg only; 0 otherwise).
    pub calibration_mode: u8,
    /// Calibration state (BikeErg only; 0 otherwise).
    pub calibration_state: u8,
    /// Calibration status (BikeErg only; 0 otherwise).
    pub calibration_status: u8,
    pub game_id: u8,
    /// Game score (16-bit).
    pub game_score: u16,
}

/// Decode an Additional Status 3 notification (12 bytes).
pub fn decode_additional_status_3(data: &[u8]) -> Result<AdditionalStatus3, BleDecodeError> {
    check_len(data, 12)?;
    Ok(AdditionalStatus3 {
        operational_state: data[0],
        workout_verification_state: data[1],
        screen_number: u16le(data[2], data[3]),
        last_error: u16le(data[4], data[5]),
        calibration_mode: data[6],
        calibration_state: data[7],
        calibration_status: data[8],
        game_id: data[9],
        game_score: u16le(data[10], data[11]),
    })
}

// ── 0x003F  Logged Workout (15 bytes) ─────────────────────────────────

/// Decoded C2 Rowing Logged Workout (UUID suffix 0x003F).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LoggedWorkout {
    /// Workout hash (8 bytes, little-endian u64).
    pub workout_hash: u64,
    /// Internal log address (32-bit).
    pub internal_log_address: u32,
    /// Logged workout size (16-bit).
    pub logged_workout_size: u16,
    pub erg_model_type: u8,
}

/// Decode a Logged Workout notification (15 bytes).
pub fn decode_logged_workout(data: &[u8]) -> Result<LoggedWorkout, BleDecodeError> {
    check_len(data, 15)?;
    let workout_hash = u64::from_le_bytes([
        data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7],
    ]);
    let internal_log_address = u32::from(data[8])
        | (u32::from(data[9]) << 8)
        | (u32::from(data[10]) << 16)
        | (u32::from(data[11]) << 24);
    Ok(LoggedWorkout {
        workout_hash,
        internal_log_address,
        logged_workout_size: u16le(data[12], data[13]),
        erg_model_type: data[14],
    })
}

// ── Multiplexed dispatch ──────────────────────────────────────────────

/// A decoded BLE notification from any rowing characteristic.
///
/// Used by [`decode_multiplexed`] to dispatch on the characteristic
/// identifier byte.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RowingCharacteristic {
    GeneralStatus(GeneralStatus),
    AdditionalStatus1(AdditionalStatus1),
    AdditionalStatus2(AdditionalStatus2),
    StrokeData(StrokeData),
    AdditionalStrokeData(AdditionalStrokeData),
    SplitIntervalData(SplitIntervalData),
    AdditionalSplitIntervalData(AdditionalSplitIntervalData),
    EndOfWorkoutSummary(EndOfWorkoutSummary),
    EndOfWorkoutAdditionalSummary(EndOfWorkoutAdditionalSummary),
    HeartRateBeltInfo(HeartRateBeltInfo),
    EndOfWorkoutAdditionalSummary2(EndOfWorkoutAdditionalSummary2),
    ForceCurveData(ForceCurveData),
    AdditionalStatus3(AdditionalStatus3),
    LoggedWorkout(LoggedWorkout),
}

/// Error from [`decode_multiplexed`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MultiplexedError {
    /// The multiplexed packet is empty (no identifier byte).
    Empty,
    /// Unknown characteristic identifier.
    UnknownId { id: u8 },
    /// The multiplexed layout differs from the dedicated characteristic
    /// layout for this ID (due to the 20-byte BLE packet limit).
    /// Mux-specific decoders are not yet implemented for these IDs.
    MuxLayoutDiffers { id: u8 },
    /// The payload after the identifier byte failed to decode.
    Decode(BleDecodeError),
}

impl fmt::Display for MultiplexedError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => write!(f, "multiplexed packet is empty"),
            Self::UnknownId { id } => {
                write!(f, "unknown multiplexed characteristic id: 0x{id:02X}")
            }
            Self::MuxLayoutDiffers { id } => {
                write!(
                    f,
                    "multiplexed layout for 0x{id:02X} differs from dedicated characteristic; \
                     mux-specific decoder not yet implemented"
                )
            }
            Self::Decode(e) => write!(f, "decode error: {e}"),
        }
    }
}

impl std::error::Error for MultiplexedError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Decode(e) => Some(e),
            _ => None,
        }
    }
}

impl From<BleDecodeError> for MultiplexedError {
    fn from(e: BleDecodeError) -> Self {
        Self::Decode(e)
    }
}

/// Decode a multiplexed notification (UUID suffix 0x0080).
///
/// The first byte identifies which rowing characteristic the payload
/// corresponds to; the remaining bytes are decoded accordingly.
///
/// **Note:** Seven multiplexed IDs (0x32, 0x33, 0x35, 0x36, 0x38, 0x39,
/// 0x3A) have layouts that differ from their dedicated characteristic
/// counterparts due to the 20-byte BLE packet limit.  These currently
/// return [`MultiplexedError::MuxLayoutDiffers`].  The remaining IDs
/// have identical layouts and are fully supported.
pub fn decode_multiplexed(data: &[u8]) -> Result<RowingCharacteristic, MultiplexedError> {
    if data.is_empty() {
        return Err(MultiplexedError::Empty);
    }
    let id = data[0];
    let payload = &data[1..];

    match id {
        // Identical layout — safe to reuse dedicated decoders.
        0x31 => Ok(RowingCharacteristic::GeneralStatus(decode_general_status(
            payload,
        )?)),
        0x37 => Ok(RowingCharacteristic::SplitIntervalData(
            decode_split_interval_data(payload)?,
        )),
        0x3B => Ok(RowingCharacteristic::HeartRateBeltInfo(
            decode_heart_rate_belt_info(payload)?,
        )),
        0x3C => Ok(RowingCharacteristic::EndOfWorkoutAdditionalSummary2(
            decode_end_of_workout_additional_summary_2(payload)?,
        )),
        0x3D => Ok(RowingCharacteristic::ForceCurveData(
            decode_force_curve_data(payload)?,
        )),
        0x3E => Ok(RowingCharacteristic::AdditionalStatus3(
            decode_additional_status_3(payload)?,
        )),
        0x3F => Ok(RowingCharacteristic::LoggedWorkout(decode_logged_workout(
            payload,
        )?)),

        // Layout differs from dedicated characteristic — mux-specific
        // decoders not yet implemented.
        0x32 | 0x33 | 0x35 | 0x36 | 0x38 | 0x39 | 0x3A => {
            Err(MultiplexedError::MuxLayoutDiffers { id })
        }

        _ => Err(MultiplexedError::UnknownId { id }),
    }
}

#[cfg(test)]
mod tests;
