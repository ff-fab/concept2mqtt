//! PyO3 wrappers for BLE notification decoders.
//!
//! Each PM5 rowing characteristic gets a `#[pyclass]` with read-only
//! field getters and a `#[pyfunction]` that decodes raw bytes.

use pyo3::prelude::*;

use crate::ble;

// ---------------------------------------------------------------------------
// Macro: generate a #[pyclass] + decode #[pyfunction] pair
// ---------------------------------------------------------------------------

macro_rules! py_ble_decoder {
    (
        $py_name:ident ($py_str_name:literal)
        decode: $rust_decode:ident => $py_decode:ident ($py_fn_name:literal)
        { $( $field:ident : $fty:ty ),* $(,)? }
    ) => {
        #[pyclass(name = $py_str_name)]
        #[derive(Clone)]
        pub struct $py_name {
            $( #[pyo3(get)] pub $field: $fty, )*
        }

        #[pymethods]
        impl $py_name {
            fn __repr__(&self) -> String {
                let fields: Vec<String> = vec![
                    $( format!("{}={:?}", stringify!($field), self.$field), )*
                ];
                format!("{}({})", $py_str_name, fields.join(", "))
            }

            fn __str__(&self) -> String {
                self.__repr__()
            }

            fn __eq__(&self, other: &Self) -> bool {
                true $( && self.$field == other.$field )*
            }
        }

        #[pyfunction(name = $py_fn_name)]
        pub fn $py_decode(data: &[u8]) -> PyResult<$py_name> {
            let r = ble::$rust_decode(data)
                .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
            Ok($py_name { $( $field: r.$field, )* })
        }
    };
}

// =========================================================================
//  0x0031  General Status (19 bytes)
// =========================================================================

py_ble_decoder! {
    PyGeneralStatus ("GeneralStatus")
    decode: decode_general_status => py_decode_general_status ("decode_general_status")
    {
        elapsed_time_cs: u32,
        distance_dm: u32,
        workout_type: u8,
        interval_type: u8,
        workout_state: u8,
        rowing_state: u8,
        stroke_state: u8,
        total_work_distance_dm: u32,
        workout_duration: u32,
        workout_duration_type: u8,
        drag_factor: u8,
    }
}

// =========================================================================
//  0x0032  Additional Status 1 (17 bytes)
// =========================================================================

py_ble_decoder! {
    PyAdditionalStatus1 ("AdditionalStatus1")
    decode: decode_additional_status_1 => py_decode_additional_status_1 ("decode_additional_status_1")
    {
        elapsed_time_cs: u32,
        speed_mms: u16,
        stroke_rate: u8,
        heartrate: u8,
        current_pace_cs: u16,
        average_pace_cs: u16,
        rest_distance: u16,
        rest_time_cs: u32,
        erg_machine_type: u8,
    }
}

// =========================================================================
//  0x0033  Additional Status 2 (20 bytes)
// =========================================================================

py_ble_decoder! {
    PyAdditionalStatus2 ("AdditionalStatus2")
    decode: decode_additional_status_2 => py_decode_additional_status_2 ("decode_additional_status_2")
    {
        elapsed_time_cs: u32,
        interval_count: u8,
        average_power: u16,
        total_calories: u16,
        split_avg_pace_cs: u16,
        split_avg_power: u16,
        split_avg_calories: u16,
        last_split_time_ds: u32,
        last_split_distance: u32,
    }
}

// =========================================================================
//  0x0035  Stroke Data (20 bytes)
// =========================================================================

py_ble_decoder! {
    PyStrokeData ("StrokeData")
    decode: decode_stroke_data => py_decode_stroke_data ("decode_stroke_data")
    {
        elapsed_time_cs: u32,
        distance_dm: u32,
        drive_length: u8,
        drive_time: u8,
        stroke_recovery_time_cs: u16,
        stroke_distance: u16,
        peak_drive_force: u16,
        average_drive_force: u16,
        work_per_stroke: u16,
        stroke_count: u16,
    }
}

// =========================================================================
//  0x0036  Additional Stroke Data (15 bytes)
// =========================================================================

py_ble_decoder! {
    PyAdditionalStrokeData ("AdditionalStrokeData")
    decode: decode_additional_stroke_data => py_decode_additional_stroke_data ("decode_additional_stroke_data")
    {
        elapsed_time_cs: u32,
        stroke_power: u16,
        stroke_calories: u16,
        stroke_count: u16,
        projected_work_time_s: u32,
        projected_work_distance: u32,
    }
}

// =========================================================================
//  0x0037  Split/Interval Data (18 bytes)
// =========================================================================

py_ble_decoder! {
    PySplitIntervalData ("SplitIntervalData")
    decode: decode_split_interval_data => py_decode_split_interval_data ("decode_split_interval_data")
    {
        elapsed_time_cs: u32,
        distance_dm: u32,
        split_interval_time_ds: u32,
        split_interval_distance: u32,
        interval_rest_time_s: u16,
        interval_rest_distance: u16,
        split_interval_type: u8,
        split_interval_number: u8,
    }
}

// =========================================================================
//  0x0038  Additional Split/Interval Data (19 bytes)
// =========================================================================

py_ble_decoder! {
    PyAdditionalSplitIntervalData ("AdditionalSplitIntervalData")
    decode: decode_additional_split_interval_data
        => py_decode_additional_split_interval_data ("decode_additional_split_interval_data")
    {
        elapsed_time_cs: u32,
        split_interval_avg_stroke_rate: u8,
        split_interval_work_heartrate: u8,
        split_interval_rest_heartrate: u8,
        split_interval_avg_pace_ds: u16,
        split_interval_total_calories: u16,
        split_interval_avg_calories: u16,
        split_interval_speed_mms: u16,
        split_interval_power: u16,
        split_avg_drag_factor: u8,
        split_interval_number: u8,
        erg_machine_type: u8,
    }
}

// =========================================================================
//  0x0039  End of Workout Summary (20 bytes)
// =========================================================================

py_ble_decoder! {
    PyEndOfWorkoutSummary ("EndOfWorkoutSummary")
    decode: decode_end_of_workout_summary
        => py_decode_end_of_workout_summary ("decode_end_of_workout_summary")
    {
        log_entry_date: u16,
        log_entry_time: u16,
        elapsed_time_cs: u32,
        distance_dm: u32,
        avg_stroke_rate: u8,
        ending_heartrate: u8,
        avg_heartrate: u8,
        min_heartrate: u8,
        max_heartrate: u8,
        avg_drag_factor: u8,
        recovery_heartrate: u8,
        workout_type: u8,
        avg_pace_ds: u16,
    }
}

// =========================================================================
//  0x003A  End of Workout Additional Summary (19 bytes)
// =========================================================================

py_ble_decoder! {
    PyEndOfWorkoutAdditionalSummary ("EndOfWorkoutAdditionalSummary")
    decode: decode_end_of_workout_additional_summary
        => py_decode_end_of_workout_additional_summary ("decode_end_of_workout_additional_summary")
    {
        log_entry_date: u16,
        log_entry_time: u16,
        split_interval_type: u8,
        split_interval_size: u16,
        split_interval_count: u8,
        total_calories: u16,
        watts: u16,
        total_rest_distance: u32,
        interval_rest_time_s: u16,
        avg_calories: u16,
    }
}

// =========================================================================
//  0x003B  Heart Rate Belt Information (6 bytes)
// =========================================================================

py_ble_decoder! {
    PyHeartRateBeltInfo ("HeartRateBeltInfo")
    decode: decode_heart_rate_belt_info
        => py_decode_heart_rate_belt_info ("decode_heart_rate_belt_info")
    {
        manufacturer_id: u8,
        device_type: u8,
        belt_id: u32,
    }
}

// =========================================================================
//  0x003C  End of Workout Additional Summary 2 (10 bytes)
// =========================================================================

py_ble_decoder! {
    PyEndOfWorkoutAdditionalSummary2 ("EndOfWorkoutAdditionalSummary2")
    decode: decode_end_of_workout_additional_summary_2
        => py_decode_end_of_workout_additional_summary_2 ("decode_end_of_workout_additional_summary_2")
    {
        log_entry_date: u16,
        log_entry_time: u16,
        avg_pace_ds: u16,
        game_identifier: u8,
        game_score: u16,
        erg_machine_type: u8,
    }
}

// =========================================================================
//  0x003D  Force Curve Data (variable, 2–20 bytes)
// =========================================================================

py_ble_decoder! {
    PyForceCurveData ("ForceCurveData")
    decode: decode_force_curve_data
        => py_decode_force_curve_data ("decode_force_curve_data")
    {
        total_notifications: u8,
        point_count: u8,
        sequence_number: u8,
        data_points: Vec<i16>,
    }
}

// =========================================================================
//  0x003E  Additional Status 3 (12 bytes)
// =========================================================================

py_ble_decoder! {
    PyAdditionalStatus3 ("AdditionalStatus3")
    decode: decode_additional_status_3
        => py_decode_additional_status_3 ("decode_additional_status_3")
    {
        operational_state: u8,
        workout_verification_state: u8,
        screen_number: u16,
        last_error: u16,
        calibration_mode: u8,
        calibration_state: u8,
        calibration_status: u8,
        game_id: u8,
        game_score: u16,
    }
}

// =========================================================================
//  0x003F  Logged Workout (15 bytes)
// =========================================================================

py_ble_decoder! {
    PyLoggedWorkout ("LoggedWorkout")
    decode: decode_logged_workout
        => py_decode_logged_workout ("decode_logged_workout")
    {
        workout_hash: u64,
        internal_log_address: u32,
        logged_workout_size: u16,
        erg_model_type: u8,
    }
}

// =========================================================================
//  0x0080  Multiplexed dispatch
// =========================================================================

/// Decode a multiplexed BLE notification (UUID suffix 0x0080).
///
/// Returns a dict with ``"type"`` (the characteristic name as a string)
/// and ``"data"`` (the decoded characteristic object).
///
/// Raises ``ValueError`` on empty data, unknown IDs, unsupported mux
/// layouts, or decode errors.
#[pyfunction(name = "decode_multiplexed")]
pub fn py_decode_multiplexed(py: Python<'_>, data: &[u8]) -> PyResult<PyObject> {
    let result = ble::decode_multiplexed(data)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

    let dict = pyo3::types::PyDict::new(py);
    match result {
        ble::RowingCharacteristic::GeneralStatus(r) => {
            dict.set_item("type", "GeneralStatus")?;
            dict.set_item("data", into_py_general_status(r).into_pyobject(py)?)?;
        }
        ble::RowingCharacteristic::AdditionalStatus1(r) => {
            dict.set_item("type", "AdditionalStatus1")?;
            dict.set_item("data", into_py_additional_status_1(r).into_pyobject(py)?)?;
        }
        ble::RowingCharacteristic::AdditionalStatus2(r) => {
            dict.set_item("type", "AdditionalStatus2")?;
            dict.set_item("data", into_py_additional_status_2(r).into_pyobject(py)?)?;
        }
        ble::RowingCharacteristic::StrokeData(r) => {
            dict.set_item("type", "StrokeData")?;
            dict.set_item("data", into_py_stroke_data(r).into_pyobject(py)?)?;
        }
        ble::RowingCharacteristic::AdditionalStrokeData(r) => {
            dict.set_item("type", "AdditionalStrokeData")?;
            dict.set_item("data", into_py_additional_stroke_data(r).into_pyobject(py)?)?;
        }
        ble::RowingCharacteristic::SplitIntervalData(r) => {
            dict.set_item("type", "SplitIntervalData")?;
            dict.set_item("data", into_py_split_interval_data(r).into_pyobject(py)?)?;
        }
        ble::RowingCharacteristic::AdditionalSplitIntervalData(r) => {
            dict.set_item("type", "AdditionalSplitIntervalData")?;
            dict.set_item(
                "data",
                into_py_additional_split_interval_data(r).into_pyobject(py)?,
            )?;
        }
        ble::RowingCharacteristic::EndOfWorkoutSummary(r) => {
            dict.set_item("type", "EndOfWorkoutSummary")?;
            dict.set_item("data", into_py_end_of_workout_summary(r).into_pyobject(py)?)?;
        }
        ble::RowingCharacteristic::EndOfWorkoutAdditionalSummary(r) => {
            dict.set_item("type", "EndOfWorkoutAdditionalSummary")?;
            dict.set_item(
                "data",
                into_py_end_of_workout_additional_summary(r).into_pyobject(py)?,
            )?;
        }
        ble::RowingCharacteristic::HeartRateBeltInfo(r) => {
            dict.set_item("type", "HeartRateBeltInfo")?;
            dict.set_item("data", into_py_heart_rate_belt_info(r).into_pyobject(py)?)?;
        }
        ble::RowingCharacteristic::EndOfWorkoutAdditionalSummary2(r) => {
            dict.set_item("type", "EndOfWorkoutAdditionalSummary2")?;
            dict.set_item(
                "data",
                into_py_end_of_workout_additional_summary_2(r).into_pyobject(py)?,
            )?;
        }
        ble::RowingCharacteristic::ForceCurveData(r) => {
            dict.set_item("type", "ForceCurveData")?;
            dict.set_item("data", into_py_force_curve_data(r).into_pyobject(py)?)?;
        }
        ble::RowingCharacteristic::AdditionalStatus3(r) => {
            dict.set_item("type", "AdditionalStatus3")?;
            dict.set_item("data", into_py_additional_status_3(r).into_pyobject(py)?)?;
        }
        ble::RowingCharacteristic::LoggedWorkout(r) => {
            dict.set_item("type", "LoggedWorkout")?;
            dict.set_item("data", into_py_logged_workout(r).into_pyobject(py)?)?;
        }
    }
    Ok(dict.into())
}

// ── Rust → Py conversion helpers (used by decode_multiplexed) ────────────

fn into_py_general_status(r: ble::GeneralStatus) -> PyGeneralStatus {
    PyGeneralStatus {
        elapsed_time_cs: r.elapsed_time_cs,
        distance_dm: r.distance_dm,
        workout_type: r.workout_type,
        interval_type: r.interval_type,
        workout_state: r.workout_state,
        rowing_state: r.rowing_state,
        stroke_state: r.stroke_state,
        total_work_distance_dm: r.total_work_distance_dm,
        workout_duration: r.workout_duration,
        workout_duration_type: r.workout_duration_type,
        drag_factor: r.drag_factor,
    }
}

fn into_py_additional_status_1(r: ble::AdditionalStatus1) -> PyAdditionalStatus1 {
    PyAdditionalStatus1 {
        elapsed_time_cs: r.elapsed_time_cs,
        speed_mms: r.speed_mms,
        stroke_rate: r.stroke_rate,
        heartrate: r.heartrate,
        current_pace_cs: r.current_pace_cs,
        average_pace_cs: r.average_pace_cs,
        rest_distance: r.rest_distance,
        rest_time_cs: r.rest_time_cs,
        erg_machine_type: r.erg_machine_type,
    }
}

fn into_py_additional_status_2(r: ble::AdditionalStatus2) -> PyAdditionalStatus2 {
    PyAdditionalStatus2 {
        elapsed_time_cs: r.elapsed_time_cs,
        interval_count: r.interval_count,
        average_power: r.average_power,
        total_calories: r.total_calories,
        split_avg_pace_cs: r.split_avg_pace_cs,
        split_avg_power: r.split_avg_power,
        split_avg_calories: r.split_avg_calories,
        last_split_time_ds: r.last_split_time_ds,
        last_split_distance: r.last_split_distance,
    }
}

fn into_py_stroke_data(r: ble::StrokeData) -> PyStrokeData {
    PyStrokeData {
        elapsed_time_cs: r.elapsed_time_cs,
        distance_dm: r.distance_dm,
        drive_length: r.drive_length,
        drive_time: r.drive_time,
        stroke_recovery_time_cs: r.stroke_recovery_time_cs,
        stroke_distance: r.stroke_distance,
        peak_drive_force: r.peak_drive_force,
        average_drive_force: r.average_drive_force,
        work_per_stroke: r.work_per_stroke,
        stroke_count: r.stroke_count,
    }
}

fn into_py_additional_stroke_data(r: ble::AdditionalStrokeData) -> PyAdditionalStrokeData {
    PyAdditionalStrokeData {
        elapsed_time_cs: r.elapsed_time_cs,
        stroke_power: r.stroke_power,
        stroke_calories: r.stroke_calories,
        stroke_count: r.stroke_count,
        projected_work_time_s: r.projected_work_time_s,
        projected_work_distance: r.projected_work_distance,
    }
}

fn into_py_split_interval_data(r: ble::SplitIntervalData) -> PySplitIntervalData {
    PySplitIntervalData {
        elapsed_time_cs: r.elapsed_time_cs,
        distance_dm: r.distance_dm,
        split_interval_time_ds: r.split_interval_time_ds,
        split_interval_distance: r.split_interval_distance,
        interval_rest_time_s: r.interval_rest_time_s,
        interval_rest_distance: r.interval_rest_distance,
        split_interval_type: r.split_interval_type,
        split_interval_number: r.split_interval_number,
    }
}

fn into_py_additional_split_interval_data(
    r: ble::AdditionalSplitIntervalData,
) -> PyAdditionalSplitIntervalData {
    PyAdditionalSplitIntervalData {
        elapsed_time_cs: r.elapsed_time_cs,
        split_interval_avg_stroke_rate: r.split_interval_avg_stroke_rate,
        split_interval_work_heartrate: r.split_interval_work_heartrate,
        split_interval_rest_heartrate: r.split_interval_rest_heartrate,
        split_interval_avg_pace_ds: r.split_interval_avg_pace_ds,
        split_interval_total_calories: r.split_interval_total_calories,
        split_interval_avg_calories: r.split_interval_avg_calories,
        split_interval_speed_mms: r.split_interval_speed_mms,
        split_interval_power: r.split_interval_power,
        split_avg_drag_factor: r.split_avg_drag_factor,
        split_interval_number: r.split_interval_number,
        erg_machine_type: r.erg_machine_type,
    }
}

fn into_py_end_of_workout_summary(r: ble::EndOfWorkoutSummary) -> PyEndOfWorkoutSummary {
    PyEndOfWorkoutSummary {
        log_entry_date: r.log_entry_date,
        log_entry_time: r.log_entry_time,
        elapsed_time_cs: r.elapsed_time_cs,
        distance_dm: r.distance_dm,
        avg_stroke_rate: r.avg_stroke_rate,
        ending_heartrate: r.ending_heartrate,
        avg_heartrate: r.avg_heartrate,
        min_heartrate: r.min_heartrate,
        max_heartrate: r.max_heartrate,
        avg_drag_factor: r.avg_drag_factor,
        recovery_heartrate: r.recovery_heartrate,
        workout_type: r.workout_type,
        avg_pace_ds: r.avg_pace_ds,
    }
}

fn into_py_end_of_workout_additional_summary(
    r: ble::EndOfWorkoutAdditionalSummary,
) -> PyEndOfWorkoutAdditionalSummary {
    PyEndOfWorkoutAdditionalSummary {
        log_entry_date: r.log_entry_date,
        log_entry_time: r.log_entry_time,
        split_interval_type: r.split_interval_type,
        split_interval_size: r.split_interval_size,
        split_interval_count: r.split_interval_count,
        total_calories: r.total_calories,
        watts: r.watts,
        total_rest_distance: r.total_rest_distance,
        interval_rest_time_s: r.interval_rest_time_s,
        avg_calories: r.avg_calories,
    }
}

fn into_py_heart_rate_belt_info(r: ble::HeartRateBeltInfo) -> PyHeartRateBeltInfo {
    PyHeartRateBeltInfo {
        manufacturer_id: r.manufacturer_id,
        device_type: r.device_type,
        belt_id: r.belt_id,
    }
}

fn into_py_end_of_workout_additional_summary_2(
    r: ble::EndOfWorkoutAdditionalSummary2,
) -> PyEndOfWorkoutAdditionalSummary2 {
    PyEndOfWorkoutAdditionalSummary2 {
        log_entry_date: r.log_entry_date,
        log_entry_time: r.log_entry_time,
        avg_pace_ds: r.avg_pace_ds,
        game_identifier: r.game_identifier,
        game_score: r.game_score,
        erg_machine_type: r.erg_machine_type,
    }
}

fn into_py_force_curve_data(r: ble::ForceCurveData) -> PyForceCurveData {
    PyForceCurveData {
        total_notifications: r.total_notifications,
        point_count: r.point_count,
        sequence_number: r.sequence_number,
        data_points: r.data_points,
    }
}

fn into_py_additional_status_3(r: ble::AdditionalStatus3) -> PyAdditionalStatus3 {
    PyAdditionalStatus3 {
        operational_state: r.operational_state,
        workout_verification_state: r.workout_verification_state,
        screen_number: r.screen_number,
        last_error: r.last_error,
        calibration_mode: r.calibration_mode,
        calibration_state: r.calibration_state,
        calibration_status: r.calibration_status,
        game_id: r.game_id,
        game_score: r.game_score,
    }
}

fn into_py_logged_workout(r: ble::LoggedWorkout) -> PyLoggedWorkout {
    PyLoggedWorkout {
        workout_hash: r.workout_hash,
        internal_log_address: r.internal_log_address,
        logged_workout_size: r.logged_workout_size,
        erg_model_type: r.erg_model_type,
    }
}

// ── Module registration ──────────────────────────────────────────────────

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Decoder classes
    m.add_class::<PyGeneralStatus>()?;
    m.add_class::<PyAdditionalStatus1>()?;
    m.add_class::<PyAdditionalStatus2>()?;
    m.add_class::<PyStrokeData>()?;
    m.add_class::<PyAdditionalStrokeData>()?;
    m.add_class::<PySplitIntervalData>()?;
    m.add_class::<PyAdditionalSplitIntervalData>()?;
    m.add_class::<PyEndOfWorkoutSummary>()?;
    m.add_class::<PyEndOfWorkoutAdditionalSummary>()?;
    m.add_class::<PyHeartRateBeltInfo>()?;
    m.add_class::<PyEndOfWorkoutAdditionalSummary2>()?;
    m.add_class::<PyForceCurveData>()?;
    m.add_class::<PyAdditionalStatus3>()?;
    m.add_class::<PyLoggedWorkout>()?;

    // Decode functions
    m.add_function(wrap_pyfunction!(py_decode_general_status, m)?)?;
    m.add_function(wrap_pyfunction!(py_decode_additional_status_1, m)?)?;
    m.add_function(wrap_pyfunction!(py_decode_additional_status_2, m)?)?;
    m.add_function(wrap_pyfunction!(py_decode_stroke_data, m)?)?;
    m.add_function(wrap_pyfunction!(py_decode_additional_stroke_data, m)?)?;
    m.add_function(wrap_pyfunction!(py_decode_split_interval_data, m)?)?;
    m.add_function(wrap_pyfunction!(
        py_decode_additional_split_interval_data,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(py_decode_end_of_workout_summary, m)?)?;
    m.add_function(wrap_pyfunction!(
        py_decode_end_of_workout_additional_summary,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(py_decode_heart_rate_belt_info, m)?)?;
    m.add_function(wrap_pyfunction!(
        py_decode_end_of_workout_additional_summary_2,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(py_decode_force_curve_data, m)?)?;
    m.add_function(wrap_pyfunction!(py_decode_additional_status_3, m)?)?;
    m.add_function(wrap_pyfunction!(py_decode_logged_workout, m)?)?;
    m.add_function(wrap_pyfunction!(py_decode_multiplexed, m)?)?;

    Ok(())
}
