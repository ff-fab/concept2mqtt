//! PyO3 wrapper classes for CSAFE command builders.
//!
//! Each proprietary command enum gets a `#[pyclass]` wrapper with
//! `#[staticmethod]` factories, plus `encode()`, `id()`, `__repr__`.

use pyo3::prelude::*;

use crate::commands;
use crate::framing;

// ---------------------------------------------------------------------------
// Macro: generate a #[pyclass] wrapping a Rust command enum
// ---------------------------------------------------------------------------

macro_rules! py_prop_command {
    (
        $(#[$meta:meta])*
        $py_name:ident ($py_str_name:literal) wraps $inner_ty:ty {
            $(unit: [ $( $u_snake:ident => $u_variant:ident ),* $(,)? ] ,)?
            $(r#struct: [ $( $s_snake:ident ( $($field:ident : $fty:ty),* ) => $s_variant:ident { $($sfield:ident),* } ),* $(,)? ] ,)?
        }
    ) => {
        $(#[$meta])*
        #[pyclass(name = $py_str_name)]
        #[derive(Clone)]
        pub struct $py_name {
            pub inner: $inner_ty,
        }

        #[pymethods]
        impl $py_name {
            fn encode(&self) -> Vec<u8> {
                self.inner.encode()
            }

            fn id(&self) -> u8 {
                self.inner.id()
            }

            fn __repr__(&self) -> String {
                format!("{:?}", self.inner)
            }

            fn __str__(&self) -> String {
                self.__repr__()
            }

            $($(
                #[staticmethod]
                fn $u_snake() -> $py_name {
                    use $inner_ty as E;
                    $py_name { inner: E::$u_variant }
                }
            )*)?

            $($(
                #[staticmethod]
                #[allow(clippy::too_many_arguments)]
                fn $s_snake( $($field : $fty),* ) -> $py_name {
                    use $inner_ty as E;
                    let inner = E::$s_variant { $($sfield),* };
                    $py_name { inner }
                }
            )*)?
        }
    };
}

// =========================================================================
//  Proprietary command wrappers
// =========================================================================

py_prop_command! {
    /// Python wrapper for PM get-configuration sub-commands.
    PyGetPmCfgCommand ("GetPmCfgCommand") wraps commands::GetPmCfgCommand {
        unit: [
            fw_version => FwVersion,
            hw_version => HwVersion,
            hw_address => HwAddress,
            tick_timebase => TickTimebase,
            hrm => Hrm,
            date_time => DateTime,
            screen_state_status => ScreenStateStatus,
            race_lane_request => RaceLaneRequest,
            race_entry_request => RaceEntryRequest,
            workout_type => WorkoutType,
            display_type => DisplayType,
            display_units => DisplayUnits,
            language_type => LanguageType,
            workout_state => WorkoutState,
            interval_type => IntervalType,
            operational_state => OperationalState,
            log_card_state => LogCardState,
            log_card_status => LogCardStatus,
            power_up_state => PowerUpState,
            rowing_state => RowingState,
            screen_content_version => ScreenContentVersion,
            communication_state => CommunicationState,
            race_participant_count => RaceParticipantCount,
            battery_level_percent => BatteryLevelPercent,
            race_mode_status => RaceModeStatus,
            internal_log_params => InternalLogParams,
            product_configuration => ProductConfiguration,
            erg_slave_discovery_request_status => ErgSlaveDiscoveryRequestStatus,
            wifi_config => WifiConfig,
            cpu_tick_rate => CpuTickRate,
            log_card_user_census => LogCardUserCensus,
            workout_interval_count => WorkoutIntervalCount,
            workout_duration => WorkoutDuration,
            work_other => WorkOther,
            extended_hrm => ExtendedHrm,
            def_calibration_verified => DefCalibrationVerified,
            flywheel_speed => FlywheelSpeed,
            erg_machine_type => ErgMachineType,
            race_begin_end_tick_count => RaceBeginEndTickCount,
            pm5_fw_update_status => Pm5FwUpdateStatus,
        ],
        r#struct: [
            erg_number(hw_address: u32) => ErgNumber { hw_address },
            erg_number_request(logical_erg_number: u8) => ErgNumberRequest { logical_erg_number },
            user_id_string(user_number: u8) => UserIdString { user_number },
            local_race_participant(hw_address: u32, user_id_string: Vec<u8>, machine_type: u8) => LocalRaceParticipant { hw_address, user_id_string, machine_type },
            user_id(user_number: u8) => UserId { user_number },
            user_profile(user_number: u8) => UserProfile { user_number },
            hr_belt_info(user_number: u8) => HrBeltInfo { user_number },
            extended_hr_belt_info(user_number: u8) => ExtendedHrBeltInfo { user_number },
            current_log_structure(structure_id: u8, split_interval_number: u8) => CurrentLogStructure { structure_id, split_interval_number },
        ],
    }
}

py_prop_command! {
    /// Python wrapper for PM get-data sub-commands.
    PyGetPmDataCommand ("GetPmDataCommand") wraps commands::GetPmDataCommand {
        unit: [
            work_time => WorkTime,
            projected_work_time => ProjectedWorkTime,
            total_rest_time => TotalRestTime,
            work_distance => WorkDistance,
            total_work_distance => TotalWorkDistance,
            projected_work_distance => ProjectedWorkDistance,
            rest_distance => RestDistance,
            total_rest_distance => TotalRestDistance,
            stroke_500m_pace => Stroke500mPace,
            stroke_power => StrokePower,
            stroke_caloric_burn_rate => StrokeCaloricBurnRate,
            split_avg_500m_pace => SplitAvg500mPace,
            split_avg_power => SplitAvgPower,
            split_avg_caloric_burn_rate => SplitAvgCaloricBurnRate,
            split_avg_calories => SplitAvgCalories,
            total_avg_500m_pace => TotalAvg500mPace,
            total_avg_power => TotalAvgPower,
            total_avg_caloric_burn_rate => TotalAvgCaloricBurnRate,
            total_avg_calories => TotalAvgCalories,
            stroke_rate => StrokeRate,
            split_avg_stroke_rate => SplitAvgStrokeRate,
            total_avg_stroke_rate => TotalAvgStrokeRate,
            avg_heart_rate => AvgHeartRate,
            ending_avg_heart_rate => EndingAvgHeartRate,
            rest_avg_heart_rate => RestAvgHeartRate,
            split_time => SplitTime,
            last_split_time => LastSplitTime,
            split_distance => SplitDistance,
            last_split_distance => LastSplitDistance,
            last_rest_distance => LastRestDistance,
            target_pace_time => TargetPaceTime,
            stroke_state => StrokeState,
            stroke_rate_state => StrokeRateState,
            drag_factor => DragFactor,
            encoder_period => EncoderPeriod,
            heart_rate_state => HeartRateState,
            sync_data => SyncData,
            sync_data_all => SyncDataAll,
            race_data => RaceData,
            tick_time => TickTime,
            error_type => ErrorType,
            error_value => ErrorValue,
            status_type => StatusType,
            status_value => StatusValue,
            epm_status => EpmStatus,
            display_update_time => DisplayUpdateTime,
            sync_fractional_time => SyncFractionalTime,
            rest_time => RestTime,
        ],
        r#struct: [
            memory(device_type: u8, start_address: u32, block_length: u8) => Memory { device_type, start_address, block_length },
            log_card_memory(start_address: u32, block_length: u8) => LogCardMemory { start_address, block_length },
            internal_log_memory(start_address: u32, block_length: u8) => InternalLogMemory { start_address, block_length },
            force_plot_data(block_length: u8) => ForcePlotData { block_length },
            heartbeat_data(block_length: u8) => HeartbeatData { block_length },
            ui_events(unused: u8) => UiEvents { unused },
            stroke_stats(unused: u8) => StrokeStats { unused },
            diag_log_record_num(record_type: u8) => DiagLogRecordNum { record_type },
            diag_log_record(record_type: u8, record_index: u16, record_offset_bytes: u16) => DiagLogRecord { record_type, record_index, record_offset_bytes },
            current_workout_hash(unused: u8) => CurrentWorkoutHash { unused },
            game_score(unused: u8) => GameScore { unused },
        ],
    }
}

py_prop_command! {
    /// Python wrapper for PM set-configuration sub-commands.
    PySetPmCfgCommand ("SetPmCfgCommand") wraps commands::SetPmCfgCommand {
        unit: [
            reset_erg_number => ResetErgNumber,
        ],
        r#struct: [
            workout_type(workout_type: u8) => WorkoutType { workout_type },
            workout_duration(duration_type: u8, duration: u32) => WorkoutDuration { duration_type, duration },
            rest_duration(duration: u16) => RestDuration { duration },
            split_duration(duration_type: u8, duration: u32) => SplitDuration { duration_type, duration },
            target_pace_time(pace_time: u32) => TargetPaceTime { pace_time },
            race_type(race_type: u8) => RaceType { race_type },
            race_lane_setup(erg_physical_address: u8, race_lane_number: u8) => RaceLaneSetup { erg_physical_address, race_lane_number },
            race_lane_verify(erg_physical_address: u8, race_lane_number: u8) => RaceLaneVerify { erg_physical_address, race_lane_number },
            race_start_params(start_type: u8, count_start: u8, ready_tick_count: u32, attention_tick_count: u32, row_tick_count: u32) => RaceStartParams { start_type, count_start, ready_tick_count, attention_tick_count, row_tick_count },
            erg_slave_discovery_request(starting_erg_slave_address: u8) => ErgSlaveDiscoveryRequest { starting_erg_slave_address },
            boat_number(boat_number: u8) => BoatNumber { boat_number },
            erg_number(hw_address: u32, erg_number: u8) => ErgNumber { hw_address, erg_number },
            screen_state(screen_type: u8, screen_value: u8) => ScreenState { screen_type, screen_value },
            configure_workout(programming_mode: u8) => ConfigureWorkout { programming_mode },
            target_avg_watts(avg_watts: u16) => TargetAvgWatts { avg_watts },
            target_cals_per_hr(cals_per_hr: u16) => TargetCalsPerHr { cals_per_hr },
            interval_type(interval_type: u8) => IntervalType { interval_type },
            workout_interval_count(interval_count: u8) => WorkoutIntervalCount { interval_count },
            display_update_rate(update_rate: u8) => DisplayUpdateRate { update_rate },
            authen_password(hw_address: u32, password: Vec<u8>) => AuthenPassword { hw_address, password },
            tick_time(tick_time: u32) => TickTime { tick_time },
            tick_time_offset(tick_time_offset: u32) => TickTimeOffset { tick_time_offset },
            race_data_sample_ticks(sample_tick: u32) => RaceDataSampleTicks { sample_tick },
            race_operation_type(operation_type: u8) => RaceOperationType { operation_type },
            race_status_display_ticks(display_tick: u32) => RaceStatusDisplayTicks { display_tick },
            race_status_warning_ticks(warning_tick: u32) => RaceStatusWarningTicks { warning_tick },
            race_idle_mode_params(doze_seconds: u16, sleep_seconds: u16) => RaceIdleModeParams { doze_seconds, sleep_seconds },
            date_time(hours: u8, minutes: u8, meridiem: u8, month: u8, day: u8, year: u16) => DateTime { hours, minutes, meridiem, month, day, year },
            language_type(language_type: u8) => LanguageType { language_type },
            wifi_config(config_index: u8, wep_mode: u8) => WifiConfig { config_index, wep_mode },
            cpu_tick_rate(cpu_tick_rate: u8) => CpuTickRate { cpu_tick_rate },
            log_card_user(user_number: u8) => LogCardUser { user_number },
            screen_error_mode(mode: u8) => ScreenErrorMode { mode },
            cable_test(mode: u8, data: Vec<u8>) => CableTest { mode, data },
            user_id(user_number: u8, user_id: u32) => UserId { user_number, user_id },
            user_profile(user_number: u8, user_weight: u16, dob_day: u8, dob_month: u8, dob_year: u16, gender: u8) => UserProfile { user_number, user_weight, dob_day, dob_month, dob_year, gender },
            hrm(mfg_id: u8, device_type: u8, device_num: u16) => Hrm { mfg_id, device_type, device_num },
            race_starting_physical_address(first_erg_address: u8) => RaceStartingPhysicalAddress { first_erg_address },
            hr_belt_info(user_number: u8, mfg_id: u8, device_type: u8, belt_id: u16) => HrBeltInfo { user_number, mfg_id, device_type, belt_id },
            sensor_channel(rf_frequency: u8, rf_period_hz: u16, datapage_pattern: u8, activity_timeout: u8) => SensorChannel { rf_frequency, rf_period_hz, datapage_pattern, activity_timeout },
        ],
    }
}

py_prop_command! {
    /// Python wrapper for PM set-data sub-commands.
    PySetPmDataCommand ("SetPmDataCommand") wraps commands::SetPmDataCommand {
        unit: [
            sync_distance => SyncDistance,
            sync_stroke_pace => SyncStrokePace,
            sync_avg_heart_rate => SyncAvgHeartRate,
            sync_time => SyncTime,
            sync_race_tick_time => SyncRaceTickTime,
            sync_data_all => SyncDataAll,
            sync_rowing_active_time => SyncRowingActiveTime,
        ],
        r#struct: [
            race_participant(racer_id: u8, racer_name: Vec<u8>) => RaceParticipant { racer_id, racer_name },
            race_status(racer1_id: u8, racer1_position: u8, racer1_delta: u32, racer2_id: u8, racer2_position: u8, racer2_delta: u32, racer3_id: u8, racer3_position: u8, racer3_delta: u32, racer4_id: u8, racer4_position: u8, racer4_delta: u32, team_distance: u32, mode: u8) => RaceStatus { racer1_id, racer1_position, racer1_delta, racer2_id, racer2_position, racer2_delta, racer3_id, racer3_position, racer3_delta, racer4_id, racer4_position, racer4_delta, team_distance, mode },
            log_card_memory(start_address: u32, block_length: u8, data: Vec<u8>) => LogCardMemory { start_address, block_length, data },
            display_string(characters: Vec<u8>) => DisplayString { characters },
            display_bitmap(bitmap_index: u16, block_length: u8, data: Vec<u8>) => DisplayBitmap { bitmap_index, block_length, data },
            local_race_participant(race_type: u8, race_length: u32, race_participants: u8, race_state: u8, race_lane: u8) => LocalRaceParticipant { race_type, race_length, race_participants, race_state, race_lane },
            game_params(game_type_id: u8, workout_duration_time: u32, split_duration_time: u32, target_pace_time: u32, target_avg_watts: u32, target_cals_per_hr: u32, target_stroke_rate: u8) => GameParams { game_type_id, workout_duration_time, split_duration_time, target_pace_time, target_avg_watts, target_cals_per_hr, target_stroke_rate },
            extended_hr_belt_info(unused: u8, mfg_id: u8, device_type: u8, belt_id: u32) => ExtendedHrBeltInfo { unused, mfg_id, device_type, belt_id },
            extended_hrm(mfg_id: u8, device_type: u8, belt_id: u32) => ExtendedHrm { mfg_id, device_type, belt_id },
            led_backlight(state: u8, intensity: u8) => LedBacklight { state, intensity },
            diag_log_record_archive(record_type: u8, record_index: u16) => DiagLogRecordArchive { record_type, record_index },
            wireless_channel_config(channel_bitmask: u32) => WirelessChannelConfig { channel_bitmask },
            race_control_params(undefined_rest_transition_time: u16, undefined_rest_interval: u16, race_prompt_bitmap_duration: u32, time_cap_duration: u32) => RaceControlParams { undefined_rest_transition_time, undefined_rest_interval, race_prompt_bitmap_duration, time_cap_duration },
        ],
    }
}

py_prop_command! {
    /// Python wrapper for SetUserCfg1 sub-commands.
    PySetUserCfg1Command ("SetUserCfg1Command") wraps commands::SetUserCfg1Command {
        r#struct: [
            workout_type(workout_type: u8) => WorkoutType { workout_type },
            workout_duration(duration_type: u8, duration: u32) => WorkoutDuration { duration_type, duration },
            split_duration(duration_type: u8, duration: u32) => SplitDuration { duration_type, duration },
            configure_workout(programming_mode: u8) => ConfigureWorkout { programming_mode },
            interval_type(interval_type: u8) => IntervalType { interval_type },
            workout_interval_count(interval_count: u8) => WorkoutIntervalCount { interval_count },
        ],
    }
}

// =========================================================================
//  PyCommand — wrapper for the public Command enum
// =========================================================================

#[pyclass(name = "Command")]
#[derive(Clone)]
pub struct PyCommand {
    pub inner: commands::Command,
}

#[pymethods]
impl PyCommand {
    fn encode(&self) -> Vec<u8> {
        self.inner.encode()
    }

    fn id(&self) -> u8 {
        self.inner.id()
    }

    fn __repr__(&self) -> String {
        format!("{:?}", self.inner)
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }

    // --- Short (unit) commands ---

    #[staticmethod]
    fn get_status() -> Self {
        Self {
            inner: commands::Command::GetStatus,
        }
    }

    #[staticmethod]
    fn reset() -> Self {
        Self {
            inner: commands::Command::Reset,
        }
    }

    #[staticmethod]
    fn go_idle() -> Self {
        Self {
            inner: commands::Command::GoIdle,
        }
    }

    #[staticmethod]
    fn go_have_id() -> Self {
        Self {
            inner: commands::Command::GoHaveId,
        }
    }

    #[staticmethod]
    fn go_in_use() -> Self {
        Self {
            inner: commands::Command::GoInUse,
        }
    }

    #[staticmethod]
    fn go_finished() -> Self {
        Self {
            inner: commands::Command::GoFinished,
        }
    }

    #[staticmethod]
    fn go_ready() -> Self {
        Self {
            inner: commands::Command::GoReady,
        }
    }

    #[staticmethod]
    fn bad_id() -> Self {
        Self {
            inner: commands::Command::BadId,
        }
    }

    #[staticmethod]
    fn get_version() -> Self {
        Self {
            inner: commands::Command::GetVersion,
        }
    }

    #[staticmethod]
    fn get_id() -> Self {
        Self {
            inner: commands::Command::GetId,
        }
    }

    #[staticmethod]
    fn get_units() -> Self {
        Self {
            inner: commands::Command::GetUnits,
        }
    }

    #[staticmethod]
    fn get_serial() -> Self {
        Self {
            inner: commands::Command::GetSerial,
        }
    }

    #[staticmethod]
    fn get_odometer() -> Self {
        Self {
            inner: commands::Command::GetOdometer,
        }
    }

    #[staticmethod]
    fn get_error_code() -> Self {
        Self {
            inner: commands::Command::GetErrorCode,
        }
    }

    #[staticmethod]
    fn get_twork() -> Self {
        Self {
            inner: commands::Command::GetTWork,
        }
    }

    #[staticmethod]
    fn get_horizontal() -> Self {
        Self {
            inner: commands::Command::GetHorizontal,
        }
    }

    #[staticmethod]
    fn get_calories() -> Self {
        Self {
            inner: commands::Command::GetCalories,
        }
    }

    #[staticmethod]
    fn get_program() -> Self {
        Self {
            inner: commands::Command::GetProgram,
        }
    }

    #[staticmethod]
    fn get_pace() -> Self {
        Self {
            inner: commands::Command::GetPace,
        }
    }

    #[staticmethod]
    fn get_cadence() -> Self {
        Self {
            inner: commands::Command::GetCadence,
        }
    }

    #[staticmethod]
    fn get_user_info() -> Self {
        Self {
            inner: commands::Command::GetUserInfo,
        }
    }

    #[staticmethod]
    fn get_heart_rate() -> Self {
        Self {
            inner: commands::Command::GetHeartRate,
        }
    }

    #[staticmethod]
    fn get_power() -> Self {
        Self {
            inner: commands::Command::GetPower,
        }
    }

    // --- Long (struct) commands ---

    #[staticmethod]
    fn auto_upload(configuration: u8) -> Self {
        Self {
            inner: commands::Command::AutoUpload { configuration },
        }
    }

    #[staticmethod]
    fn id_digits(count: u8) -> Self {
        Self {
            inner: commands::Command::IdDigits { count },
        }
    }

    #[staticmethod]
    fn set_time(hour: u8, minute: u8, second: u8) -> Self {
        Self {
            inner: commands::Command::SetTime {
                hour,
                minute,
                second,
            },
        }
    }

    #[staticmethod]
    fn set_date(year: u8, month: u8, day: u8) -> Self {
        Self {
            inner: commands::Command::SetDate { year, month, day },
        }
    }

    #[staticmethod]
    fn set_timeout(timeout: u8) -> Self {
        Self {
            inner: commands::Command::SetTimeout { timeout },
        }
    }

    #[staticmethod]
    fn set_twork(hours: u8, minutes: u8, seconds: u8) -> Self {
        Self {
            inner: commands::Command::SetTWork {
                hours,
                minutes,
                seconds,
            },
        }
    }

    #[staticmethod]
    fn set_horizontal(distance_lsb: u8, distance_msb: u8, units: u8) -> Self {
        Self {
            inner: commands::Command::SetHorizontal {
                distance_lsb,
                distance_msb,
                units,
            },
        }
    }

    #[staticmethod]
    fn set_calories(calories_lsb: u8, calories_msb: u8) -> Self {
        Self {
            inner: commands::Command::SetCalories {
                calories_lsb,
                calories_msb,
            },
        }
    }

    #[staticmethod]
    fn set_program(program: u8, unused: u8) -> Self {
        Self {
            inner: commands::Command::SetProgram { program, unused },
        }
    }

    #[staticmethod]
    fn set_power(watts_lsb: u8, watts_msb: u8, units: u8) -> Self {
        Self {
            inner: commands::Command::SetPower {
                watts_lsb,
                watts_msb,
                units,
            },
        }
    }

    #[staticmethod]
    fn get_caps(capability_code: u8) -> Self {
        Self {
            inner: commands::Command::GetCaps { capability_code },
        }
    }

    // --- Wrapper commands (accept lists of sub-commands) ---

    #[staticmethod]
    fn set_user_cfg1(commands: Vec<PySetUserCfg1Command>) -> Self {
        Self {
            inner: commands::Command::SetUserCfg1 {
                commands: commands.into_iter().map(|c| c.inner).collect(),
            },
        }
    }

    #[staticmethod]
    fn set_pm_cfg(commands: Vec<PySetPmCfgCommand>) -> Self {
        Self {
            inner: commands::Command::SetPmCfg {
                commands: commands.into_iter().map(|c| c.inner).collect(),
            },
        }
    }

    #[staticmethod]
    fn set_pm_data(commands: Vec<PySetPmDataCommand>) -> Self {
        Self {
            inner: commands::Command::SetPmData {
                commands: commands.into_iter().map(|c| c.inner).collect(),
            },
        }
    }

    #[staticmethod]
    fn get_pm_cfg(commands: Vec<PyGetPmCfgCommand>) -> Self {
        Self {
            inner: commands::Command::GetPmCfg {
                commands: commands.into_iter().map(|c| c.inner).collect(),
            },
        }
    }

    #[staticmethod]
    fn get_pm_data(commands: Vec<PyGetPmDataCommand>) -> Self {
        Self {
            inner: commands::Command::GetPmData {
                commands: commands.into_iter().map(|c| c.inner).collect(),
            },
        }
    }
}

// =========================================================================
//  Top-level encoding functions
// =========================================================================

/// Encode a list of commands into raw contents bytes (no framing).
#[pyfunction(name = "encode_commands")]
fn py_encode_commands(commands: Vec<PyCommand>) -> Vec<u8> {
    let cmds: Vec<commands::Command> = commands.into_iter().map(|c| c.inner).collect();
    commands::encode_commands(&cmds)
}

/// Encode commands and wrap in a standard CSAFE frame.
#[pyfunction(name = "build_command_frame")]
fn py_build_command_frame(commands: Vec<PyCommand>) -> PyResult<Vec<u8>> {
    let contents = py_encode_commands(commands);
    framing::build_standard_frame(&contents)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

// =========================================================================
//  Module registration
// =========================================================================

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyGetPmCfgCommand>()?;
    m.add_class::<PyGetPmDataCommand>()?;
    m.add_class::<PySetPmCfgCommand>()?;
    m.add_class::<PySetPmDataCommand>()?;
    m.add_class::<PySetUserCfg1Command>()?;
    m.add_class::<PyCommand>()?;
    m.add_function(wrap_pyfunction!(py_encode_commands, m)?)?;
    m.add_function(wrap_pyfunction!(py_build_command_frame, m)?)?;
    Ok(())
}
