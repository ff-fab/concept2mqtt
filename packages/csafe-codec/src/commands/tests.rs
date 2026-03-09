use super::*;

// -- WorkoutType ------------------------------------------------------

#[test]
fn workout_type_try_from_valid() {
    let cases: &[(u8, WorkoutType)] = &[
        (0, WorkoutType::JustRowNoSplits),
        (1, WorkoutType::JustRowSplits),
        (2, WorkoutType::FixedDistNoSplits),
        (3, WorkoutType::FixedDistSplits),
        (4, WorkoutType::FixedTimeNoSplits),
        (5, WorkoutType::FixedTimeSplits),
        (6, WorkoutType::FixedTimeInterval),
        (7, WorkoutType::FixedDistInterval),
        (8, WorkoutType::VariableInterval),
        (9, WorkoutType::VariableUndefinedRestInterval),
        (10, WorkoutType::FixedCalorieSplits),
        (11, WorkoutType::FixedWattMinuteSplits),
        (12, WorkoutType::FixedCalorieInterval),
    ];
    for &(raw, expected) in cases {
        assert_eq!(WorkoutType::try_from(raw), Ok(expected));
    }
}

#[test]
fn workout_type_try_from_invalid() {
    // 13 is NUM in the spec — deliberately excluded.
    assert!(WorkoutType::try_from(13).is_err());
    assert!(WorkoutType::try_from(255).is_err());
}

#[test]
fn workout_type_display() {
    assert_eq!(WorkoutType::JustRowNoSplits.to_string(), "JustRowNoSplits");
    assert_eq!(
        WorkoutType::VariableInterval.to_string(),
        "VariableInterval"
    );
}

// -- IntervalType -----------------------------------------------------

#[test]
fn interval_type_try_from_valid() {
    for raw in 0..=9u8 {
        assert!(IntervalType::try_from(raw).is_ok());
    }
}

#[test]
fn interval_type_none_is_255() {
    assert_eq!(IntervalType::try_from(255), Ok(IntervalType::None));
}

#[test]
fn interval_type_try_from_invalid() {
    assert!(IntervalType::try_from(10).is_err());
    assert!(IntervalType::try_from(254).is_err());
}

// -- WorkoutState -----------------------------------------------------

#[test]
fn workout_state_try_from_valid() {
    for raw in 0..=13u8 {
        assert!(WorkoutState::try_from(raw).is_ok());
    }
}

#[test]
fn workout_state_try_from_invalid() {
    assert!(WorkoutState::try_from(14).is_err());
}

#[test]
fn workout_state_display() {
    assert_eq!(WorkoutState::Rearm.to_string(), "Rearm");
}

// -- RowingState ------------------------------------------------------

#[test]
fn rowing_state_try_from_valid() {
    assert_eq!(RowingState::try_from(0), Ok(RowingState::Inactive));
    assert_eq!(RowingState::try_from(1), Ok(RowingState::Active));
}

#[test]
fn rowing_state_try_from_invalid() {
    assert!(RowingState::try_from(2).is_err());
}

// -- StrokeState ------------------------------------------------------

#[test]
fn stroke_state_try_from_valid() {
    for raw in 0..=4u8 {
        assert!(StrokeState::try_from(raw).is_ok());
    }
}

#[test]
fn stroke_state_try_from_invalid() {
    assert!(StrokeState::try_from(5).is_err());
}

// -- DurationType -----------------------------------------------------

#[test]
fn duration_type_try_from_valid() {
    assert_eq!(DurationType::try_from(0x00), Ok(DurationType::Time));
    assert_eq!(DurationType::try_from(0x40), Ok(DurationType::Calories));
    assert_eq!(DurationType::try_from(0x80), Ok(DurationType::Distance));
    assert_eq!(DurationType::try_from(0xC0), Ok(DurationType::WattMinutes));
}

#[test]
fn duration_type_try_from_invalid() {
    assert!(DurationType::try_from(0x01).is_err());
    assert!(DurationType::try_from(0x41).is_err());
}

// -- ScreenType -------------------------------------------------------

#[test]
fn screen_type_try_from_valid() {
    for raw in 0..=5u8 {
        assert!(ScreenType::try_from(raw).is_ok());
    }
}

#[test]
fn screen_type_try_from_invalid() {
    assert!(ScreenType::try_from(6).is_err());
}

// -- ErgMachineType ---------------------------------------------------

#[test]
fn erg_machine_type_try_from_valid() {
    let valid: &[u8] = &[
        0, 1, 2, 3, 5, 7, 8, 16, 17, 18, 19, 20, 32, 64, 128, 143, 192, 193, 194, 207, 224, 225,
        226,
    ];
    for &raw in valid {
        assert!(
            ErgMachineType::try_from(raw).is_ok(),
            "expected Ok for {raw}"
        );
    }
}

#[test]
fn erg_machine_type_try_from_invalid() {
    assert!(ErgMachineType::try_from(4).is_err());
    assert!(ErgMachineType::try_from(6).is_err());
    assert!(ErgMachineType::try_from(255).is_err());
}

#[test]
fn erg_machine_type_display() {
    assert_eq!(ErgMachineType::StaticSki.to_string(), "StaticSki");
    assert_eq!(ErgMachineType::Bike.to_string(), "Bike");
}

// -- Command ID mapping -----------------------------------------------

#[test]
fn command_id_short_commands() {
    let cases: &[(Command, u8)] = &[
        (Command::GetStatus, 0x80),
        (Command::Reset, 0x81),
        (Command::GoIdle, 0x82),
        (Command::GoHaveId, 0x83),
        (Command::GoInUse, 0x85),
        (Command::GoFinished, 0x86),
        (Command::GoReady, 0x87),
        (Command::BadId, 0x88),
        (Command::GetVersion, 0x91),
        (Command::GetId, 0x92),
        (Command::GetUnits, 0x93),
        (Command::GetSerial, 0x94),
        (Command::GetOdometer, 0x9B),
        (Command::GetErrorCode, 0x9C),
        (Command::GetTWork, 0xA0),
        (Command::GetHorizontal, 0xA1),
        (Command::GetCalories, 0xA3),
        (Command::GetProgram, 0xA4),
        (Command::GetPace, 0xA6),
        (Command::GetCadence, 0xA7),
        (Command::GetUserInfo, 0xAB),
        (Command::GetHeartRate, 0xB0),
        (Command::GetPower, 0xB4),
    ];
    for (cmd, expected_id) in cases {
        assert_eq!(cmd.id(), *expected_id, "mismatch for {cmd:?}");
    }
}

#[test]
fn command_id_long_commands() {
    let cases: &[(Command, u8)] = &[
        (Command::AutoUpload { configuration: 0 }, 0x01),
        (Command::IdDigits { count: 5 }, 0x10),
        (
            Command::SetTime {
                hour: 0,
                minute: 0,
                second: 0,
            },
            0x11,
        ),
        (
            Command::SetDate {
                year: 0,
                month: 0,
                day: 0,
            },
            0x12,
        ),
        (Command::SetTimeout { timeout: 0 }, 0x13),
        (
            Command::SetTWork {
                hours: 0,
                minutes: 0,
                seconds: 0,
            },
            0x20,
        ),
        (
            Command::SetHorizontal {
                distance_lsb: 0,
                distance_msb: 0,
                units: 0,
            },
            0x21,
        ),
        (
            Command::SetCalories {
                calories_lsb: 0,
                calories_msb: 0,
            },
            0x23,
        ),
        (
            Command::SetProgram {
                program: 0,
                unused: 0,
            },
            0x24,
        ),
        (
            Command::SetPower {
                watts_lsb: 0,
                watts_msb: 0,
                units: 0,
            },
            0x34,
        ),
        (Command::GetCaps { capability_code: 0 }, 0x70),
    ];
    for (cmd, expected_id) in cases {
        assert_eq!(cmd.id(), *expected_id, "mismatch for {cmd:?}");
    }
}

#[test]
fn command_is_short_returns_true_for_short() {
    assert!(Command::GetStatus.is_short());
    assert!(Command::GetPower.is_short());
    assert!(Command::GetSerial.is_short());
}

#[test]
fn command_is_short_returns_false_for_long() {
    assert!(!Command::AutoUpload { configuration: 1 }.is_short());
    assert!(!Command::SetTime {
        hour: 12,
        minute: 0,
        second: 0,
    }
    .is_short());
    assert!(!Command::GetCaps { capability_code: 1 }.is_short());
}

#[test]
fn command_id_wrappers() {
    let cases: &[(Command, u8)] = &[
        (Command::SetUserCfg1 { commands: vec![] }, 0x1A),
        (Command::SetPmCfg { commands: vec![] }, 0x76),
        (Command::SetPmData { commands: vec![] }, 0x77),
        (Command::GetPmCfg { commands: vec![] }, 0x7E),
        (Command::GetPmData { commands: vec![] }, 0x7F),
    ];
    for (cmd, expected_id) in cases {
        assert_eq!(cmd.id(), *expected_id, "mismatch for {cmd:?}");
    }
}

// -- GetPmCfgCommand --------------------------------------------------

#[test]
fn get_pm_cfg_command_id_short() {
    let cases: &[(GetPmCfgCommand, u8)] = &[
        (GetPmCfgCommand::FwVersion, 0x80),
        (GetPmCfgCommand::HwVersion, 0x81),
        (GetPmCfgCommand::DateTime, 0x85),
        (GetPmCfgCommand::WorkoutType, 0x89),
        (GetPmCfgCommand::WorkoutState, 0x8D),
        (GetPmCfgCommand::RowingState, 0x93),
        (GetPmCfgCommand::BatteryLevelPercent, 0x97),
        (GetPmCfgCommand::WorkoutIntervalCount, 0x9F),
        (GetPmCfgCommand::WorkoutDuration, 0xE8),
        (GetPmCfgCommand::ErgMachineType, 0xED),
        (GetPmCfgCommand::Pm5FwUpdateStatus, 0xEF),
    ];
    for (cmd, expected_id) in cases {
        assert_eq!(cmd.id(), *expected_id, "mismatch for {cmd:?}");
    }
}

#[test]
fn get_pm_cfg_command_id_long() {
    let cases: &[(GetPmCfgCommand, u8)] = &[
        (GetPmCfgCommand::ErgNumber { hw_address: 0 }, 0x50),
        (
            GetPmCfgCommand::ErgNumberRequest {
                logical_erg_number: 1,
            },
            0x51,
        ),
        (GetPmCfgCommand::UserIdString { user_number: 0 }, 0x52),
        (GetPmCfgCommand::UserId { user_number: 0 }, 0x54),
        (
            GetPmCfgCommand::CurrentLogStructure {
                structure_id: 0,
                split_interval_number: 1,
            },
            0x58,
        ),
    ];
    for (cmd, expected_id) in cases {
        assert_eq!(cmd.id(), *expected_id, "mismatch for {cmd:?}");
    }
}

#[test]
fn get_pm_cfg_command_is_short() {
    assert!(GetPmCfgCommand::FwVersion.is_short());
    assert!(GetPmCfgCommand::WorkoutDuration.is_short());
    assert!(!GetPmCfgCommand::ErgNumber { hw_address: 0 }.is_short());
    assert!(!GetPmCfgCommand::CurrentLogStructure {
        structure_id: 0,
        split_interval_number: 0
    }
    .is_short());
}

// -- GetPmDataCommand -------------------------------------------------

#[test]
fn get_pm_data_command_id_short() {
    let cases: &[(GetPmDataCommand, u8)] = &[
        (GetPmDataCommand::WorkTime, 0xA0),
        (GetPmDataCommand::WorkDistance, 0xA3),
        (GetPmDataCommand::StrokeRate, 0xB3),
        (GetPmDataCommand::AvgHeartRate, 0xB6),
        (GetPmDataCommand::DragFactor, 0xC1),
        (GetPmDataCommand::RaceData, 0xC6),
        (GetPmDataCommand::RestTime, 0xCF),
    ];
    for (cmd, expected_id) in cases {
        assert_eq!(cmd.id(), *expected_id, "mismatch for {cmd:?}");
    }
}

#[test]
fn get_pm_data_command_id_long() {
    let cases: &[(GetPmDataCommand, u8)] = &[
        (
            GetPmDataCommand::Memory {
                device_type: 0,
                start_address: 0,
                block_length: 64,
            },
            0x68,
        ),
        (GetPmDataCommand::ForcePlotData { block_length: 32 }, 0x6B),
        (GetPmDataCommand::StrokeStats { unused: 0 }, 0x6E),
        (
            GetPmDataCommand::DiagLogRecord {
                record_type: 0,
                record_index: 0,
                record_offset_bytes: 0,
            },
            0x71,
        ),
        (GetPmDataCommand::GameScore { unused: 0 }, 0x78),
    ];
    for (cmd, expected_id) in cases {
        assert_eq!(cmd.id(), *expected_id, "mismatch for {cmd:?}");
    }
}

#[test]
fn get_pm_data_command_is_short() {
    assert!(GetPmDataCommand::WorkTime.is_short());
    assert!(GetPmDataCommand::RestTime.is_short());
    assert!(!GetPmDataCommand::Memory {
        device_type: 0,
        start_address: 0,
        block_length: 0
    }
    .is_short());
    assert!(!GetPmDataCommand::GameScore { unused: 0 }.is_short());
}

// -- SetPmCfgCommand --------------------------------------------------

#[test]
fn set_pm_cfg_command_id() {
    let cases: &[(SetPmCfgCommand, u8)] = &[
        (SetPmCfgCommand::ResetErgNumber, 0xE1),
        (SetPmCfgCommand::WorkoutType { workout_type: 0 }, 0x01),
        (
            SetPmCfgCommand::SplitDuration {
                duration_type: 0,
                duration: 0,
            },
            0x05,
        ),
        (
            SetPmCfgCommand::ScreenState {
                screen_type: 0,
                screen_value: 0,
            },
            0x13,
        ),
        (
            SetPmCfgCommand::ConfigureWorkout {
                programming_mode: 1,
            },
            0x14,
        ),
        (
            SetPmCfgCommand::SensorChannel {
                rf_frequency: 0,
                rf_period_hz: 0,
                datapage_pattern: 0,
                activity_timeout: 0,
            },
            0x2F,
        ),
    ];
    for (cmd, expected_id) in cases {
        assert_eq!(cmd.id(), *expected_id, "mismatch for {cmd:?}");
    }
}

// -- SetPmDataCommand -------------------------------------------------

#[test]
fn set_pm_data_command_id() {
    let cases: &[(SetPmDataCommand, u8)] = &[
        (SetPmDataCommand::SyncDistance, 0xD0),
        (SetPmDataCommand::SyncTime, 0xD3),
        (SetPmDataCommand::SyncDataAll, 0xD8),
        (
            SetPmDataCommand::RaceParticipant {
                racer_id: 1,
                racer_name: vec![],
            },
            0x32,
        ),
        (
            SetPmDataCommand::GameParams {
                game_type_id: 0,
                workout_duration_time: 0,
                split_duration_time: 0,
                target_pace_time: 0,
                target_avg_watts: 0,
                target_cals_per_hr: 0,
                target_stroke_rate: 0,
            },
            0x38,
        ),
        (
            SetPmDataCommand::RaceControlParams {
                undefined_rest_transition_time: 0,
                undefined_rest_interval: 0,
                race_prompt_bitmap_duration: 0,
                time_cap_duration: 0,
            },
            0x3E,
        ),
    ];
    for (cmd, expected_id) in cases {
        assert_eq!(cmd.id(), *expected_id, "mismatch for {cmd:?}");
    }
}

// -- SetUserCfg1Command -----------------------------------------------

#[test]
fn set_user_cfg1_command_id() {
    let cases: &[(SetUserCfg1Command, u8)] = &[
        (SetUserCfg1Command::WorkoutType { workout_type: 0 }, 0x01),
        (
            SetUserCfg1Command::WorkoutDuration {
                duration_type: 0,
                duration: 0,
            },
            0x03,
        ),
        (
            SetUserCfg1Command::SplitDuration {
                duration_type: 0,
                duration: 0,
            },
            0x05,
        ),
        (
            SetUserCfg1Command::ConfigureWorkout {
                programming_mode: 1,
            },
            0x14,
        ),
        (SetUserCfg1Command::IntervalType { interval_type: 0 }, 0x17),
        (
            SetUserCfg1Command::WorkoutIntervalCount { interval_count: 0 },
            0x18,
        ),
    ];
    for (cmd, expected_id) in cases {
        assert_eq!(cmd.id(), *expected_id, "mismatch for {cmd:?}");
    }
}

#[test]
fn set_user_cfg1_command_is_short() {
    // All SetUserCfg1 commands are long.
    assert!(!SetUserCfg1Command::WorkoutType { workout_type: 0 }.is_short());
    assert!(!SetUserCfg1Command::SplitDuration {
        duration_type: 0,
        duration: 0
    }
    .is_short());
}

// -- Wrapper type safety ----------------------------------------------

#[test]
fn command_wrapper_typed() {
    let cmd = Command::GetPmCfg {
        commands: vec![GetPmCfgCommand::FwVersion, GetPmCfgCommand::WorkoutType],
    };
    assert_eq!(cmd.id(), 0x7E);

    let cmd = Command::SetPmCfg {
        commands: vec![SetPmCfgCommand::ConfigureWorkout {
            programming_mode: 1,
        }],
    };
    assert_eq!(cmd.id(), 0x76);

    let cmd = Command::SetUserCfg1 {
        commands: vec![
            SetUserCfg1Command::WorkoutType { workout_type: 2 },
            SetUserCfg1Command::SplitDuration {
                duration_type: 0x80,
                duration: 2000,
            },
        ],
    };
    assert_eq!(cmd.id(), 0x1A);
}
