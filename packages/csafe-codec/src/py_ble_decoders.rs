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
        $py_name:ident ($py_str_name:literal) for $rust_type:ident
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

        impl From<ble::$rust_type> for $py_name {
            fn from(r: ble::$rust_type) -> Self {
                Self { $( $field: r.$field, )* }
            }
        }

        #[pyfunction(name = $py_fn_name)]
        pub fn $py_decode(data: &[u8]) -> PyResult<$py_name> {
            let r = ble::$rust_decode(data)
                .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
            Ok(r.into())
        }
    };
}

// =========================================================================
//  0x0031  General Status (19 bytes)
// =========================================================================

py_ble_decoder! {
    PyGeneralStatus ("GeneralStatus") for GeneralStatus
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
    PyAdditionalStatus1 ("AdditionalStatus1") for AdditionalStatus1
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
    PyAdditionalStatus2 ("AdditionalStatus2") for AdditionalStatus2
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
    PyStrokeData ("StrokeData") for StrokeData
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
    PyAdditionalStrokeData ("AdditionalStrokeData") for AdditionalStrokeData
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
    PySplitIntervalData ("SplitIntervalData") for SplitIntervalData
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
    PyAdditionalSplitIntervalData ("AdditionalSplitIntervalData") for AdditionalSplitIntervalData
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
    PyEndOfWorkoutSummary ("EndOfWorkoutSummary") for EndOfWorkoutSummary
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
    PyEndOfWorkoutAdditionalSummary ("EndOfWorkoutAdditionalSummary") for EndOfWorkoutAdditionalSummary
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
    PyHeartRateBeltInfo ("HeartRateBeltInfo") for HeartRateBeltInfo
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
    PyEndOfWorkoutAdditionalSummary2 ("EndOfWorkoutAdditionalSummary2") for EndOfWorkoutAdditionalSummary2
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
    PyForceCurveData ("ForceCurveData") for ForceCurveData
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
    PyAdditionalStatus3 ("AdditionalStatus3") for AdditionalStatus3
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
    PyLoggedWorkout ("LoggedWorkout") for LoggedWorkout
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

    // Helper macro to reduce repetition in match arms
    macro_rules! mux_arm {
        ($dict:ident, $py:ident, $name:literal, $r:ident => $py_type:ty) => {{
            $dict.set_item("type", $name)?;
            let converted: $py_type = $r.into();
            $dict.set_item("data", converted.into_pyobject($py)?)?;
        }};
    }

    let dict = pyo3::types::PyDict::new(py);
    match result {
        ble::RowingCharacteristic::GeneralStatus(r) => {
            mux_arm!(dict, py, "GeneralStatus", r => PyGeneralStatus)
        }
        ble::RowingCharacteristic::AdditionalStatus1(r) => {
            mux_arm!(dict, py, "AdditionalStatus1", r => PyAdditionalStatus1)
        }
        ble::RowingCharacteristic::AdditionalStatus2(r) => {
            mux_arm!(dict, py, "AdditionalStatus2", r => PyAdditionalStatus2)
        }
        ble::RowingCharacteristic::StrokeData(r) => {
            mux_arm!(dict, py, "StrokeData", r => PyStrokeData)
        }
        ble::RowingCharacteristic::AdditionalStrokeData(r) => {
            mux_arm!(dict, py, "AdditionalStrokeData", r => PyAdditionalStrokeData)
        }
        ble::RowingCharacteristic::SplitIntervalData(r) => {
            mux_arm!(dict, py, "SplitIntervalData", r => PySplitIntervalData)
        }
        ble::RowingCharacteristic::AdditionalSplitIntervalData(r) => {
            mux_arm!(dict, py, "AdditionalSplitIntervalData", r => PyAdditionalSplitIntervalData)
        }
        ble::RowingCharacteristic::EndOfWorkoutSummary(r) => {
            mux_arm!(dict, py, "EndOfWorkoutSummary", r => PyEndOfWorkoutSummary)
        }
        ble::RowingCharacteristic::EndOfWorkoutAdditionalSummary(r) => {
            mux_arm!(dict, py, "EndOfWorkoutAdditionalSummary", r => PyEndOfWorkoutAdditionalSummary)
        }
        ble::RowingCharacteristic::HeartRateBeltInfo(r) => {
            mux_arm!(dict, py, "HeartRateBeltInfo", r => PyHeartRateBeltInfo)
        }
        ble::RowingCharacteristic::EndOfWorkoutAdditionalSummary2(r) => {
            mux_arm!(dict, py, "EndOfWorkoutAdditionalSummary2", r => PyEndOfWorkoutAdditionalSummary2)
        }
        ble::RowingCharacteristic::ForceCurveData(r) => {
            mux_arm!(dict, py, "ForceCurveData", r => PyForceCurveData)
        }
        ble::RowingCharacteristic::AdditionalStatus3(r) => {
            mux_arm!(dict, py, "AdditionalStatus3", r => PyAdditionalStatus3)
        }
        ble::RowingCharacteristic::LoggedWorkout(r) => {
            mux_arm!(dict, py, "LoggedWorkout", r => PyLoggedWorkout)
        }
    }
    Ok(dict.into())
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
