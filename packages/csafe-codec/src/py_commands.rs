//! PyO3 bindings for CSAFE command types and enums.

use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::commands;

// ---------------------------------------------------------------------------
// Macro: generate a name-lookup function and a values-dict function per enum
// ---------------------------------------------------------------------------

macro_rules! py_enum_bindings {
    ($enum_ty:ty, $name_fn:ident, $values_fn:ident, $py_name:expr, $py_values:expr,
     [ $( $variant:ident = $val:expr ),+ $(,)? ]
    ) => {
        #[pyfunction(name = $py_name)]
        fn $name_fn(value: u8) -> PyResult<String> {
            <$enum_ty>::try_from(value)
                .map(|v| v.to_string())
                .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
        }

        #[pyfunction(name = $py_values)]
        fn $values_fn(py: Python<'_>) -> PyResult<PyObject> {
            let dict = PyDict::new(py);
            $( dict.set_item(stringify!($variant), $val as u8)?; )+
            Ok(dict.into_any().unbind())
        }
    };
}

// --- Generate bindings for all 8 value enums ---

py_enum_bindings!(
    commands::WorkoutType,
    py_workout_type_name,
    py_workout_type_values,
    "workout_type_name",
    "workout_type_values",
    [
        JustRowNoSplits = 0,
        JustRowSplits = 1,
        FixedDistNoSplits = 2,
        FixedDistSplits = 3,
        FixedTimeNoSplits = 4,
        FixedTimeSplits = 5,
        FixedTimeInterval = 6,
        FixedDistInterval = 7,
        VariableInterval = 8,
        VariableUndefinedRestInterval = 9,
        FixedCalorieSplits = 10,
        FixedWattMinuteSplits = 11,
        FixedCalorieInterval = 12,
    ]
);

py_enum_bindings!(
    commands::IntervalType,
    py_interval_type_name,
    py_interval_type_values,
    "interval_type_name",
    "interval_type_values",
    [
        Time = 0,
        Dist = 1,
        Rest = 2,
        TimeRestUndefined = 3,
        DistRestUndefined = 4,
        RestUndefined = 5,
        Calorie = 6,
        CalorieRestUndefined = 7,
        WattMinute = 8,
        WattMinuteRestUndefined = 9,
        None = 255,
    ]
);

py_enum_bindings!(
    commands::WorkoutState,
    py_workout_state_name,
    py_workout_state_values,
    "workout_state_name",
    "workout_state_values",
    [
        WaitToBegin = 0,
        WorkoutRow = 1,
        CountdownPause = 2,
        IntervalRest = 3,
        IntervalWorkTime = 4,
        IntervalWorkDistance = 5,
        IntervalRestEndToWorkTime = 6,
        IntervalRestEndToWorkDistance = 7,
        IntervalWorkTimeToRest = 8,
        IntervalWorkDistanceToRest = 9,
        WorkoutEnd = 10,
        Terminate = 11,
        WorkoutLogged = 12,
        Rearm = 13,
    ]
);

py_enum_bindings!(
    commands::RowingState,
    py_rowing_state_name,
    py_rowing_state_values,
    "rowing_state_name",
    "rowing_state_values",
    [Inactive = 0, Active = 1,]
);

py_enum_bindings!(
    commands::StrokeState,
    py_stroke_state_name,
    py_stroke_state_values,
    "stroke_state_name",
    "stroke_state_values",
    [
        WaitingForWheelToReachMinSpeed = 0,
        WaitingForWheelToAccelerate = 1,
        Driving = 2,
        DwellingAfterDrive = 3,
        Recovery = 4,
    ]
);

py_enum_bindings!(
    commands::DurationType,
    py_duration_type_name,
    py_duration_type_values,
    "duration_type_name",
    "duration_type_values",
    [
        Time = 0x00,
        Calories = 0x40,
        Distance = 0x80,
        WattMinutes = 0xC0,
    ]
);

py_enum_bindings!(
    commands::ScreenType,
    py_screen_type_name,
    py_screen_type_values,
    "screen_type_name",
    "screen_type_values",
    [
        None = 0,
        Workout = 1,
        Race = 2,
        Csafe = 3,
        Diag = 4,
        Mfg = 5,
    ]
);

py_enum_bindings!(
    commands::ErgMachineType,
    py_erg_machine_type_name,
    py_erg_machine_type_values,
    "erg_machine_type_name",
    "erg_machine_type_values",
    [
        StaticD = 0,
        StaticC = 1,
        StaticA = 2,
        StaticB = 3,
        StaticE = 5,
        StaticSimulator = 7,
        StaticDynamic = 8,
        SlidesA = 16,
        SlidesB = 17,
        SlidesC = 18,
        SlidesD = 19,
        SlidesE = 20,
        LinkedDynamic = 32,
        StaticDyno = 64,
        StaticSki = 128,
        StaticSkiSimulator = 143,
        Bike = 192,
        BikeArms = 193,
        BikeNoArms = 194,
        BikeSimulator = 207,
        MultiergRow = 224,
        MultiergSki = 225,
        MultiergBike = 226,
    ]
);

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

/// Register command-related Python bindings on the module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Enum name-lookup functions
    m.add_function(wrap_pyfunction!(py_workout_type_name, m)?)?;
    m.add_function(wrap_pyfunction!(py_interval_type_name, m)?)?;
    m.add_function(wrap_pyfunction!(py_workout_state_name, m)?)?;
    m.add_function(wrap_pyfunction!(py_rowing_state_name, m)?)?;
    m.add_function(wrap_pyfunction!(py_stroke_state_name, m)?)?;
    m.add_function(wrap_pyfunction!(py_duration_type_name, m)?)?;
    m.add_function(wrap_pyfunction!(py_screen_type_name, m)?)?;
    m.add_function(wrap_pyfunction!(py_erg_machine_type_name, m)?)?;

    // Enum values-dict functions
    m.add_function(wrap_pyfunction!(py_workout_type_values, m)?)?;
    m.add_function(wrap_pyfunction!(py_interval_type_values, m)?)?;
    m.add_function(wrap_pyfunction!(py_workout_state_values, m)?)?;
    m.add_function(wrap_pyfunction!(py_rowing_state_values, m)?)?;
    m.add_function(wrap_pyfunction!(py_stroke_state_values, m)?)?;
    m.add_function(wrap_pyfunction!(py_duration_type_values, m)?)?;
    m.add_function(wrap_pyfunction!(py_screen_type_values, m)?)?;
    m.add_function(wrap_pyfunction!(py_erg_machine_type_values, m)?)?;

    // Public command ID constants — short commands (0x80–0xFF)
    m.add("CMD_GET_STATUS", 0x80u8)?;
    m.add("CMD_RESET", 0x81u8)?;
    m.add("CMD_GO_IDLE", 0x82u8)?;
    m.add("CMD_GO_HAVE_ID", 0x83u8)?;
    m.add("CMD_GO_IN_USE", 0x85u8)?;
    m.add("CMD_GO_FINISHED", 0x86u8)?;
    m.add("CMD_GO_READY", 0x87u8)?;
    m.add("CMD_BAD_ID", 0x88u8)?;
    m.add("CMD_GET_VERSION", 0x91u8)?;
    m.add("CMD_GET_ID", 0x92u8)?;
    m.add("CMD_GET_UNITS", 0x93u8)?;
    m.add("CMD_GET_SERIAL", 0x94u8)?;
    m.add("CMD_GET_ODOMETER", 0x9Bu8)?;
    m.add("CMD_GET_ERROR_CODE", 0x9Cu8)?;
    m.add("CMD_GET_TWORK", 0xA0u8)?;
    m.add("CMD_GET_HORIZONTAL", 0xA1u8)?;
    m.add("CMD_GET_CALORIES", 0xA3u8)?;
    m.add("CMD_GET_PROGRAM", 0xA4u8)?;
    m.add("CMD_GET_PACE", 0xA6u8)?;
    m.add("CMD_GET_CADENCE", 0xA7u8)?;
    m.add("CMD_GET_USER_INFO", 0xABu8)?;
    m.add("CMD_GET_HEART_RATE", 0xB0u8)?;
    m.add("CMD_GET_POWER", 0xB4u8)?;

    // Public command ID constants — long commands (0x01–0x70)
    m.add("CMD_AUTO_UPLOAD", 0x01u8)?;
    m.add("CMD_ID_DIGITS", 0x10u8)?;
    m.add("CMD_SET_TIME", 0x11u8)?;
    m.add("CMD_SET_DATE", 0x12u8)?;
    m.add("CMD_SET_TIMEOUT", 0x13u8)?;
    m.add("CMD_SET_TWORK", 0x20u8)?;
    m.add("CMD_SET_HORIZONTAL", 0x21u8)?;
    m.add("CMD_SET_CALORIES", 0x23u8)?;
    m.add("CMD_SET_PROGRAM", 0x24u8)?;
    m.add("CMD_SET_POWER", 0x34u8)?;
    m.add("CMD_GET_CAPS", 0x70u8)?;

    // PM wrapper command ID constants
    m.add("CMD_SET_USER_CFG1", 0x1Au8)?;
    m.add("CMD_SET_PM_CFG", 0x76u8)?;
    m.add("CMD_SET_PM_DATA", 0x77u8)?;
    m.add("CMD_GET_PM_CFG", 0x7Eu8)?;
    m.add("CMD_GET_PM_DATA", 0x7Fu8)?;

    Ok(())
}
