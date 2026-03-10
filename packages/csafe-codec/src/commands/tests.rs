use super::*;
use crate::framing::FrameBuf;

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

// -- Encode: short public commands ------------------------------------

#[test]
fn encode_all_short_commands_single_byte() {
    let short_cmds: &[(Command, u8)] = &[
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
    for (cmd, expected) in short_cmds {
        assert_eq!(cmd.encode(), vec![*expected], "encode mismatch for {cmd:?}");
    }
}

// -- Encode: long public commands -------------------------------------

#[test]
fn encode_auto_upload() {
    assert_eq!(
        Command::AutoUpload {
            configuration: 0xAB
        }
        .encode(),
        vec![0x01, 0x01, 0xAB]
    );
}

#[test]
fn encode_set_time() {
    assert_eq!(
        Command::SetTime {
            hour: 14,
            minute: 30,
            second: 0
        }
        .encode(),
        vec![0x11, 0x03, 14, 30, 0]
    );
}

#[test]
fn encode_set_date() {
    assert_eq!(
        Command::SetDate {
            year: 26,
            month: 3,
            day: 9
        }
        .encode(),
        vec![0x12, 0x03, 26, 3, 9]
    );
}

#[test]
fn encode_set_timeout() {
    assert_eq!(
        Command::SetTimeout { timeout: 60 }.encode(),
        vec![0x13, 0x01, 60]
    );
}

#[test]
fn encode_set_horizontal() {
    assert_eq!(
        Command::SetHorizontal {
            distance_lsb: 0xE8,
            distance_msb: 0x03,
            units: 0x24
        }
        .encode(),
        vec![0x21, 0x03, 0xE8, 0x03, 0x24]
    );
}

#[test]
fn encode_set_calories() {
    assert_eq!(
        Command::SetCalories {
            calories_lsb: 0xF4,
            calories_msb: 0x01
        }
        .encode(),
        vec![0x23, 0x02, 0xF4, 0x01]
    );
}

#[test]
fn encode_set_program() {
    assert_eq!(
        Command::SetProgram {
            program: 5,
            unused: 0
        }
        .encode(),
        vec![0x24, 0x02, 5, 0]
    );
}

#[test]
fn encode_set_power() {
    assert_eq!(
        Command::SetPower {
            watts_lsb: 0xC8,
            watts_msb: 0x00,
            units: 0x24
        }
        .encode(),
        vec![0x34, 0x03, 0xC8, 0x00, 0x24]
    );
}

#[test]
fn encode_get_caps() {
    assert_eq!(
        Command::GetCaps {
            capability_code: 0x02
        }
        .encode(),
        vec![0x70, 0x01, 0x02]
    );
}

#[test]
fn encode_id_digits() {
    assert_eq!(Command::IdDigits { count: 5 }.encode(), vec![0x10, 0x01, 5]);
}

#[test]
fn encode_set_twork() {
    assert_eq!(
        Command::SetTWork {
            hours: 1,
            minutes: 30,
            seconds: 0
        }
        .encode(),
        vec![0x20, 0x03, 1, 30, 0]
    );
}

// -- Encode: wrapper commands -----------------------------------------

#[test]
fn encode_wrapper_empty() {
    let cmd = Command::GetPmCfg { commands: vec![] };
    assert_eq!(cmd.encode(), vec![0x7E, 0x00]);
}

#[test]
fn encode_wrapper_get_pm_cfg_short_sub() {
    let cmd = Command::GetPmCfg {
        commands: vec![GetPmCfgCommand::FwVersion, GetPmCfgCommand::HwVersion],
    };
    assert_eq!(cmd.encode(), vec![0x7E, 0x02, 0x80, 0x81]);
}

#[test]
fn encode_wrapper_get_pm_cfg_long_sub() {
    let cmd = Command::GetPmCfg {
        commands: vec![GetPmCfgCommand::ErgNumberRequest {
            logical_erg_number: 3,
        }],
    };
    assert_eq!(cmd.encode(), vec![0x7E, 0x03, 0x51, 0x01, 3]);
}

#[test]
fn encode_wrapper_set_user_cfg1() {
    let cmd = Command::SetUserCfg1 {
        commands: vec![
            SetUserCfg1Command::WorkoutType { workout_type: 2 },
            SetUserCfg1Command::IntervalType { interval_type: 1 },
        ],
    };
    // sub1: [0x01, 1, 2] = 3 bytes; sub2: [0x17, 1, 1] = 3 bytes; total = 6
    assert_eq!(cmd.encode(), vec![0x1A, 0x06, 0x01, 1, 2, 0x17, 1, 1]);
}

#[test]
fn encode_wrapper_set_pm_data_short_sub() {
    let cmd = Command::SetPmData {
        commands: vec![SetPmDataCommand::SyncDistance],
    };
    assert_eq!(cmd.encode(), vec![0x77, 0x01, 0xD0]);
}

// -- encode_commands --------------------------------------------------

#[test]
fn encode_commands_multiple() {
    let cmds = vec![
        Command::GetStatus,
        Command::GoIdle,
        Command::GetCaps { capability_code: 1 },
    ];
    assert_eq!(encode_commands(&cmds), vec![0x80, 0x82, 0x70, 0x01, 1]);
}

#[test]
fn encode_commands_empty() {
    let empty: Vec<u8> = vec![];
    assert_eq!(encode_commands(&[]), empty);
}

// -- Encode: proprietary sub-command samples --------------------------

#[test]
fn encode_get_pm_cfg_erg_number() {
    let cmd = GetPmCfgCommand::ErgNumber {
        hw_address: 0x01020304,
    };
    assert_eq!(cmd.encode(), vec![0x50, 4, 0x04, 0x03, 0x02, 0x01]);
}

#[test]
fn encode_get_pm_cfg_current_log_structure() {
    let cmd = GetPmCfgCommand::CurrentLogStructure {
        structure_id: 1,
        split_interval_number: 5,
    };
    assert_eq!(cmd.encode(), vec![0x58, 2, 1, 5]);
}

#[test]
fn encode_get_pm_cfg_local_race_participant() {
    let cmd = GetPmCfgCommand::LocalRaceParticipant {
        hw_address: 0x00000001,
        user_id_string: vec![0x41, 0x42],
        machine_type: 5,
    };
    assert_eq!(
        cmd.encode(),
        vec![0x53, 7, 0x01, 0x00, 0x00, 0x00, 0x41, 0x42, 5]
    );
}

#[test]
fn encode_get_pm_data_memory() {
    let cmd = GetPmDataCommand::Memory {
        device_type: 1,
        start_address: 0x00001000,
        block_length: 32,
    };
    assert_eq!(cmd.encode(), vec![0x68, 6, 1, 0x00, 0x10, 0x00, 0x00, 32]);
}

#[test]
fn encode_get_pm_data_diag_log_record() {
    let cmd = GetPmDataCommand::DiagLogRecord {
        record_type: 2,
        record_index: 0x0100,
        record_offset_bytes: 0x0040,
    };
    assert_eq!(cmd.encode(), vec![0x71, 5, 2, 0x00, 0x01, 0x40, 0x00]);
}

#[test]
fn encode_get_pm_data_short() {
    assert_eq!(GetPmDataCommand::WorkTime.encode(), vec![0xA0]);
    assert_eq!(GetPmDataCommand::DragFactor.encode(), vec![0xC1]);
}

#[test]
fn encode_set_pm_cfg_workout_duration() {
    let cmd = SetPmCfgCommand::WorkoutDuration {
        duration_type: 0x00,
        duration: 300,
    };
    let mut expected = vec![0x03, 5, 0x00];
    expected.extend_from_slice(&300u32.to_le_bytes());
    assert_eq!(cmd.encode(), expected);
}

#[test]
fn encode_set_pm_cfg_reset_erg_number_short() {
    assert_eq!(SetPmCfgCommand::ResetErgNumber.encode(), vec![0xE1]);
}

#[test]
fn encode_set_pm_cfg_authen_password() {
    let cmd = SetPmCfgCommand::AuthenPassword {
        hw_address: 0xAABBCCDD,
        password: vec![1, 2, 3],
    };
    assert_eq!(cmd.encode(), vec![0x1A, 7, 0xDD, 0xCC, 0xBB, 0xAA, 1, 2, 3]);
}

#[test]
fn encode_set_pm_cfg_hrm() {
    let cmd = SetPmCfgCommand::Hrm {
        mfg_id: 1,
        device_type: 120,
        device_num: 0x1234,
    };
    assert_eq!(cmd.encode(), vec![0x2B, 4, 1, 120, 0x34, 0x12]);
}

#[test]
fn encode_set_pm_cfg_sensor_channel() {
    let cmd = SetPmCfgCommand::SensorChannel {
        rf_frequency: 57,
        rf_period_hz: 8070,
        datapage_pattern: 1,
        activity_timeout: 30,
    };
    let mut expected = vec![0x2F, 5, 57];
    expected.extend_from_slice(&8070u16.to_le_bytes());
    expected.push(1);
    expected.push(30);
    assert_eq!(cmd.encode(), expected);
}

#[test]
fn encode_set_pm_data_race_participant() {
    let cmd = SetPmDataCommand::RaceParticipant {
        racer_id: 1,
        racer_name: vec![0x41, 0x42, 0x43],
    };
    assert_eq!(cmd.encode(), vec![0x32, 4, 1, 0x41, 0x42, 0x43]);
}

#[test]
fn encode_set_pm_data_display_string() {
    let cmd = SetPmDataCommand::DisplayString {
        characters: vec![0x48, 0x49],
    };
    assert_eq!(cmd.encode(), vec![0x35, 2, 0x48, 0x49]);
}

#[test]
fn encode_set_pm_data_short() {
    assert_eq!(SetPmDataCommand::SyncDistance.encode(), vec![0xD0]);
    assert_eq!(SetPmDataCommand::SyncDataAll.encode(), vec![0xD8]);
}

#[test]
fn encode_set_pm_data_led_backlight() {
    let cmd = SetPmDataCommand::LedBacklight {
        state: 1,
        intensity: 200,
    };
    assert_eq!(cmd.encode(), vec![0x3B, 2, 1, 200]);
}

#[test]
fn encode_set_user_cfg1_workout_duration() {
    let cmd = SetUserCfg1Command::WorkoutDuration {
        duration_type: 0x00,
        duration: 1200,
    };
    let mut expected = vec![0x03, 5, 0x00];
    expected.extend_from_slice(&1200u32.to_le_bytes());
    assert_eq!(cmd.encode(), expected);
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

// -- encode_into / encode_commands_into --------------------------------

#[test]
fn encode_into_short_command() {
    let mut buf = FrameBuf::new();
    Command::GetStatus.encode_into(&mut buf);
    assert_eq!(&buf[..], &[0x80]);
}

#[test]
fn encode_into_long_command() {
    let mut buf = FrameBuf::new();
    Command::SetTime {
        hour: 14,
        minute: 30,
        second: 0,
    }
    .encode_into(&mut buf);
    assert_eq!(&buf[..], &[0x11, 0x03, 14, 30, 0]);
}

#[test]
fn encode_into_wrapper_command() {
    let mut buf = FrameBuf::new();
    Command::GetPmCfg {
        commands: vec![GetPmCfgCommand::FwVersion, GetPmCfgCommand::HwVersion],
    }
    .encode_into(&mut buf);
    assert_eq!(&buf[..], &[0x7E, 0x02, 0x80, 0x81]);
}

#[test]
fn encode_commands_into_multiple() {
    let mut buf = FrameBuf::new();
    let cmds = vec![
        Command::GetStatus,
        Command::GoIdle,
        Command::GetCaps { capability_code: 1 },
    ];
    encode_commands_into(&cmds, &mut buf);
    assert_eq!(&buf[..], &[0x80, 0x82, 0x70, 0x01, 1]);
}

#[test]
fn encode_into_proprietary_sub_command() {
    let mut buf = FrameBuf::new();
    GetPmCfgCommand::ErgNumber {
        hw_address: 0x01020304,
    }
    .encode_into(&mut buf);
    assert_eq!(&buf[..], &[0x50, 4, 0x04, 0x03, 0x02, 0x01]);
}
