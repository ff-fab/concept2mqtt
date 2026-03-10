//! Proprietary (Concept2 PM) commands sent inside wrapper commands.
//!
//! Each enum corresponds to one wrapper command and holds the proprietary
//! sub-commands that may be sent through it.

// =========================================================================
//  GetPmCfgCommand — wrapper 0x7E (CSAFE_GETPMCFG_CMD)
// =========================================================================

/// Proprietary get-configuration commands sent inside `CSAFE_GETPMCFG_CMD` (0x7E).
///
/// Short commands (0x80–0x9F, 0xE8–0xEF) are unit variants.
/// Long commands (0x50–0x58) carry request fields.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum GetPmCfgCommand {
    // --- Short get config (0x80–0x9F) ---
    /// Firmware version (0x80).
    FwVersion,
    /// Hardware version (0x81).
    HwVersion,
    /// Hardware address / serial (0x82).
    HwAddress,
    /// Tick timebase (0x83).
    TickTimebase,
    /// Heart rate monitor info (0x84).
    Hrm,
    /// Date and time (0x85).
    DateTime,
    /// Screen state status (0x86).
    ScreenStateStatus,
    /// Race lane request (0x87).
    RaceLaneRequest,
    /// Race entry request (0x88).
    RaceEntryRequest,
    /// Workout type (0x89).
    WorkoutType,
    /// Display type (0x8A).
    DisplayType,
    /// Display units (0x8B).
    DisplayUnits,
    /// Language type (0x8C).
    LanguageType,
    /// Workout state (0x8D).
    WorkoutState,
    /// Interval type (0x8E).
    IntervalType,
    /// Operational state (0x8F).
    OperationalState,
    /// Log card state (0x90).
    LogCardState,
    /// Log card status (0x91).
    LogCardStatus,
    /// Power-up state (0x92).
    PowerUpState,
    /// Rowing state (0x93).
    RowingState,
    /// Screen content version (0x94).
    ScreenContentVersion,
    /// Communication state (0x95).
    CommunicationState,
    /// Race participant count (0x96).
    RaceParticipantCount,
    /// Battery level percent (0x97).
    BatteryLevelPercent,
    /// Race mode status (0x98).
    RaceModeStatus,
    /// Internal log params (0x99).
    InternalLogParams,
    /// Product configuration (0x9A).
    ProductConfiguration,
    /// Erg slave discovery request status (0x9B).
    ErgSlaveDiscoveryRequestStatus,
    /// WiFi configuration (0x9C).
    WifiConfig,
    /// CPU tick rate (0x9D).
    CpuTickRate,
    /// Log card user census (0x9E).
    LogCardUserCensus,
    /// Workout interval count (0x9F).
    WorkoutIntervalCount,

    // --- Short get config extended (0xE8–0xEF) ---
    /// Workout duration (0xE8).
    WorkoutDuration,
    /// Work other (0xE9).
    WorkOther,
    /// Extended HRM info (0xEA).
    ExtendedHrm,
    /// Default calibration verified (0xEB).
    DefCalibrationVerified,
    /// Flywheel speed (0xEC).
    FlywheelSpeed,
    /// Erg machine type (0xED).
    ErgMachineType,
    /// Race begin/end tick count (0xEE).
    RaceBeginEndTickCount,
    /// PM5 firmware update status (0xEF).
    Pm5FwUpdateStatus,

    // --- Long get config (0x50–0x58) ---
    /// Get erg number by HW address (0x50).
    ErgNumber { hw_address: u32 },
    /// Get erg number request (0x51).
    ErgNumberRequest { logical_erg_number: u8 },
    /// Get user ID string (0x52).
    UserIdString { user_number: u8 },
    /// Get local race participant (0x53).
    LocalRaceParticipant {
        hw_address: u32,
        user_id_string: Vec<u8>,
        machine_type: u8,
    },
    /// Get user ID (0x54).
    UserId { user_number: u8 },
    /// Get user profile (0x55).
    UserProfile { user_number: u8 },
    /// Get HR belt info (0x56).
    HrBeltInfo { user_number: u8 },
    /// Get extended HR belt info (0x57).
    ExtendedHrBeltInfo { user_number: u8 },
    /// Get current log structure (0x58).
    CurrentLogStructure {
        structure_id: u8,
        split_interval_number: u8,
    },
}

impl GetPmCfgCommand {
    /// Returns the proprietary command ID byte.
    pub fn id(&self) -> u8 {
        match self {
            Self::FwVersion => 0x80,
            Self::HwVersion => 0x81,
            Self::HwAddress => 0x82,
            Self::TickTimebase => 0x83,
            Self::Hrm => 0x84,
            Self::DateTime => 0x85,
            Self::ScreenStateStatus => 0x86,
            Self::RaceLaneRequest => 0x87,
            Self::RaceEntryRequest => 0x88,
            Self::WorkoutType => 0x89,
            Self::DisplayType => 0x8A,
            Self::DisplayUnits => 0x8B,
            Self::LanguageType => 0x8C,
            Self::WorkoutState => 0x8D,
            Self::IntervalType => 0x8E,
            Self::OperationalState => 0x8F,
            Self::LogCardState => 0x90,
            Self::LogCardStatus => 0x91,
            Self::PowerUpState => 0x92,
            Self::RowingState => 0x93,
            Self::ScreenContentVersion => 0x94,
            Self::CommunicationState => 0x95,
            Self::RaceParticipantCount => 0x96,
            Self::BatteryLevelPercent => 0x97,
            Self::RaceModeStatus => 0x98,
            Self::InternalLogParams => 0x99,
            Self::ProductConfiguration => 0x9A,
            Self::ErgSlaveDiscoveryRequestStatus => 0x9B,
            Self::WifiConfig => 0x9C,
            Self::CpuTickRate => 0x9D,
            Self::LogCardUserCensus => 0x9E,
            Self::WorkoutIntervalCount => 0x9F,
            Self::WorkoutDuration => 0xE8,
            Self::WorkOther => 0xE9,
            Self::ExtendedHrm => 0xEA,
            Self::DefCalibrationVerified => 0xEB,
            Self::FlywheelSpeed => 0xEC,
            Self::ErgMachineType => 0xED,
            Self::RaceBeginEndTickCount => 0xEE,
            Self::Pm5FwUpdateStatus => 0xEF,
            Self::ErgNumber { .. } => 0x50,
            Self::ErgNumberRequest { .. } => 0x51,
            Self::UserIdString { .. } => 0x52,
            Self::LocalRaceParticipant { .. } => 0x53,
            Self::UserId { .. } => 0x54,
            Self::UserProfile { .. } => 0x55,
            Self::HrBeltInfo { .. } => 0x56,
            Self::ExtendedHrBeltInfo { .. } => 0x57,
            Self::CurrentLogStructure { .. } => 0x58,
        }
    }

    /// Returns `true` if this is a short command (no request data).
    pub fn is_short(&self) -> bool {
        self.id() & 0x80 != 0
    }

    /// Encode this sub-command into raw wire bytes.
    pub fn encode(&self) -> Vec<u8> {
        if self.is_short() {
            return vec![self.id()];
        }
        match self {
            Self::ErgNumber { hw_address } => {
                let mut v = vec![0x50, 4];
                v.extend_from_slice(&hw_address.to_le_bytes());
                v
            }
            Self::ErgNumberRequest { logical_erg_number } => {
                vec![0x51, 1, *logical_erg_number]
            }
            Self::UserIdString { user_number } => vec![0x52, 1, *user_number],
            Self::LocalRaceParticipant {
                hw_address,
                user_id_string,
                machine_type,
            } => {
                let len = 4 + user_id_string.len() + 1;
                let mut v = vec![0x53, len as u8];
                v.extend_from_slice(&hw_address.to_le_bytes());
                v.extend_from_slice(user_id_string);
                v.push(*machine_type);
                v
            }
            Self::UserId { user_number } => vec![0x54, 1, *user_number],
            Self::UserProfile { user_number } => vec![0x55, 1, *user_number],
            Self::HrBeltInfo { user_number } => vec![0x56, 1, *user_number],
            Self::ExtendedHrBeltInfo { user_number } => vec![0x57, 1, *user_number],
            Self::CurrentLogStructure {
                structure_id,
                split_interval_number,
            } => {
                vec![0x58, 2, *structure_id, *split_interval_number]
            }
            _ => unreachable!(),
        }
    }
}

// =========================================================================
//  GetPmDataCommand — wrapper 0x7F (CSAFE_GETPMDATA_CMD)
// =========================================================================

/// Proprietary get-data commands sent inside `CSAFE_GETPMDATA_CMD` (0x7F).
///
/// Short commands (0xA0–0xCF) are unit variants.
/// Long commands (0x68–0x72, 0x78) carry request fields.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum GetPmDataCommand {
    // --- Short get data (0xA0–0xCF) ---
    /// Work time (0xA0).
    WorkTime,
    /// Projected work time (0xA1).
    ProjectedWorkTime,
    /// Total rest time (0xA2).
    TotalRestTime,
    /// Work distance (0xA3).
    WorkDistance,
    /// Total work distance (0xA4).
    TotalWorkDistance,
    /// Projected work distance (0xA5).
    ProjectedWorkDistance,
    /// Rest distance (0xA6).
    RestDistance,
    /// Total rest distance (0xA7).
    TotalRestDistance,
    /// Stroke 500m pace (0xA8).
    Stroke500mPace,
    /// Stroke power (0xA9).
    StrokePower,
    /// Stroke caloric burn rate (0xAA).
    StrokeCaloricBurnRate,
    /// Split average 500m pace (0xAB).
    SplitAvg500mPace,
    /// Split average power (0xAC).
    SplitAvgPower,
    /// Split average caloric burn rate (0xAD).
    SplitAvgCaloricBurnRate,
    /// Split average calories (0xAE).
    SplitAvgCalories,
    /// Total average 500m pace (0xAF).
    TotalAvg500mPace,
    /// Total average power (0xB0).
    TotalAvgPower,
    /// Total average caloric burn rate (0xB1).
    TotalAvgCaloricBurnRate,
    /// Total average calories (0xB2).
    TotalAvgCalories,
    /// Stroke rate (0xB3).
    StrokeRate,
    /// Split average stroke rate (0xB4).
    SplitAvgStrokeRate,
    /// Total average stroke rate (0xB5).
    TotalAvgStrokeRate,
    /// Average heart rate (0xB6).
    AvgHeartRate,
    /// Ending average heart rate (0xB7).
    EndingAvgHeartRate,
    /// Rest average heart rate (0xB8).
    RestAvgHeartRate,
    /// Split time (0xB9).
    SplitTime,
    /// Last split time (0xBA).
    LastSplitTime,
    /// Split distance (0xBB).
    SplitDistance,
    /// Last split distance (0xBC).
    LastSplitDistance,
    /// Last rest distance (0xBD).
    LastRestDistance,
    /// Target pace time (0xBE).
    TargetPaceTime,
    /// Stroke state (0xBF).
    StrokeState,
    /// Stroke rate state (0xC0).
    StrokeRateState,
    /// Drag factor (0xC1).
    DragFactor,
    /// Encoder period (0xC2).
    EncoderPeriod,
    /// Heart rate state (0xC3).
    HeartRateState,
    /// Sync data (0xC4).
    SyncData,
    /// Sync data all (0xC5).
    SyncDataAll,
    /// Race data (0xC6).
    RaceData,
    /// Tick time (0xC7).
    TickTime,
    /// Error type (0xC8).
    ErrorType,
    /// Error value (0xC9).
    ErrorValue,
    /// Status type (0xCA).
    StatusType,
    /// Status value (0xCB).
    StatusValue,
    /// EPM status (0xCC).
    EpmStatus,
    /// Display update time (0xCD).
    DisplayUpdateTime,
    /// Sync fractional time (0xCE).
    SyncFractionalTime,
    /// Rest time (0xCF).
    RestTime,

    // --- Long get data (0x68–0x72, 0x78) ---
    /// Read memory block (0x68).
    Memory {
        device_type: u8,
        start_address: u32,
        block_length: u8,
    },
    /// Read logcard memory (0x69).
    LogCardMemory {
        start_address: u32,
        block_length: u8,
    },
    /// Read internal log memory (0x6A).
    InternalLogMemory {
        start_address: u32,
        block_length: u8,
    },
    /// Force plot data (0x6B).
    ForcePlotData { block_length: u8 },
    /// Heartbeat data (0x6C).
    HeartbeatData { block_length: u8 },
    /// UI events (0x6D).
    UiEvents { unused: u8 },
    /// Stroke stats (0x6E).
    StrokeStats { unused: u8 },
    /// Diagnostic log record number (0x70).
    DiagLogRecordNum { record_type: u8 },
    /// Diagnostic log record (0x71).
    DiagLogRecord {
        record_type: u8,
        record_index: u16,
        record_offset_bytes: u16,
    },
    /// Current workout hash (0x72).
    CurrentWorkoutHash { unused: u8 },
    /// Game score (0x78).
    GameScore { unused: u8 },
}

impl GetPmDataCommand {
    /// Returns the proprietary command ID byte.
    pub fn id(&self) -> u8 {
        match self {
            Self::WorkTime => 0xA0,
            Self::ProjectedWorkTime => 0xA1,
            Self::TotalRestTime => 0xA2,
            Self::WorkDistance => 0xA3,
            Self::TotalWorkDistance => 0xA4,
            Self::ProjectedWorkDistance => 0xA5,
            Self::RestDistance => 0xA6,
            Self::TotalRestDistance => 0xA7,
            Self::Stroke500mPace => 0xA8,
            Self::StrokePower => 0xA9,
            Self::StrokeCaloricBurnRate => 0xAA,
            Self::SplitAvg500mPace => 0xAB,
            Self::SplitAvgPower => 0xAC,
            Self::SplitAvgCaloricBurnRate => 0xAD,
            Self::SplitAvgCalories => 0xAE,
            Self::TotalAvg500mPace => 0xAF,
            Self::TotalAvgPower => 0xB0,
            Self::TotalAvgCaloricBurnRate => 0xB1,
            Self::TotalAvgCalories => 0xB2,
            Self::StrokeRate => 0xB3,
            Self::SplitAvgStrokeRate => 0xB4,
            Self::TotalAvgStrokeRate => 0xB5,
            Self::AvgHeartRate => 0xB6,
            Self::EndingAvgHeartRate => 0xB7,
            Self::RestAvgHeartRate => 0xB8,
            Self::SplitTime => 0xB9,
            Self::LastSplitTime => 0xBA,
            Self::SplitDistance => 0xBB,
            Self::LastSplitDistance => 0xBC,
            Self::LastRestDistance => 0xBD,
            Self::TargetPaceTime => 0xBE,
            Self::StrokeState => 0xBF,
            Self::StrokeRateState => 0xC0,
            Self::DragFactor => 0xC1,
            Self::EncoderPeriod => 0xC2,
            Self::HeartRateState => 0xC3,
            Self::SyncData => 0xC4,
            Self::SyncDataAll => 0xC5,
            Self::RaceData => 0xC6,
            Self::TickTime => 0xC7,
            Self::ErrorType => 0xC8,
            Self::ErrorValue => 0xC9,
            Self::StatusType => 0xCA,
            Self::StatusValue => 0xCB,
            Self::EpmStatus => 0xCC,
            Self::DisplayUpdateTime => 0xCD,
            Self::SyncFractionalTime => 0xCE,
            Self::RestTime => 0xCF,
            Self::Memory { .. } => 0x68,
            Self::LogCardMemory { .. } => 0x69,
            Self::InternalLogMemory { .. } => 0x6A,
            Self::ForcePlotData { .. } => 0x6B,
            Self::HeartbeatData { .. } => 0x6C,
            Self::UiEvents { .. } => 0x6D,
            Self::StrokeStats { .. } => 0x6E,
            Self::DiagLogRecordNum { .. } => 0x70,
            Self::DiagLogRecord { .. } => 0x71,
            Self::CurrentWorkoutHash { .. } => 0x72,
            Self::GameScore { .. } => 0x78,
        }
    }

    /// Returns `true` if this is a short command (no request data).
    pub fn is_short(&self) -> bool {
        self.id() & 0x80 != 0
    }

    /// Encode this sub-command into raw wire bytes.
    pub fn encode(&self) -> Vec<u8> {
        if self.is_short() {
            return vec![self.id()];
        }
        match self {
            Self::Memory {
                device_type,
                start_address,
                block_length,
            } => {
                let mut v = vec![0x68, 6, *device_type];
                v.extend_from_slice(&start_address.to_le_bytes());
                v.push(*block_length);
                v
            }
            Self::LogCardMemory {
                start_address,
                block_length,
            } => {
                let mut v = vec![0x69, 5];
                v.extend_from_slice(&start_address.to_le_bytes());
                v.push(*block_length);
                v
            }
            Self::InternalLogMemory {
                start_address,
                block_length,
            } => {
                let mut v = vec![0x6A, 5];
                v.extend_from_slice(&start_address.to_le_bytes());
                v.push(*block_length);
                v
            }
            Self::ForcePlotData { block_length } => vec![0x6B, 1, *block_length],
            Self::HeartbeatData { block_length } => vec![0x6C, 1, *block_length],
            Self::UiEvents { unused } => vec![0x6D, 1, *unused],
            Self::StrokeStats { unused } => vec![0x6E, 1, *unused],
            Self::DiagLogRecordNum { record_type } => vec![0x70, 1, *record_type],
            Self::DiagLogRecord {
                record_type,
                record_index,
                record_offset_bytes,
            } => {
                let mut v = vec![0x71, 5, *record_type];
                v.extend_from_slice(&record_index.to_le_bytes());
                v.extend_from_slice(&record_offset_bytes.to_le_bytes());
                v
            }
            Self::CurrentWorkoutHash { unused } => vec![0x72, 1, *unused],
            Self::GameScore { unused } => vec![0x78, 1, *unused],
            _ => unreachable!(),
        }
    }
}

// =========================================================================
//  SetPmCfgCommand — wrapper 0x76 (CSAFE_SETPMCFG_CMD)
// =========================================================================

/// Proprietary set-configuration commands sent inside `CSAFE_SETPMCFG_CMD` (0x76).
///
/// Includes one short command (0xE1) and long commands (0x01–0x2F).
/// Commands marked `not_implemented` in the spec are omitted.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum SetPmCfgCommand {
    // --- Short (0xE1) ---
    /// Reset erg number (0xE1).
    ResetErgNumber,

    // --- Long set config ---
    /// Set workout type (0x01).
    WorkoutType { workout_type: u8 },
    /// Set workout duration (0x03).
    WorkoutDuration { duration_type: u8, duration: u32 },
    /// Set rest duration (0x04).
    RestDuration { duration: u16 },
    /// Set split duration (0x05).
    SplitDuration { duration_type: u8, duration: u32 },
    /// Set target pace time (0x06).
    TargetPaceTime { pace_time: u32 },
    /// Set race type (0x09).
    RaceType { race_type: u8 },
    /// Set race lane setup (0x0B).
    RaceLaneSetup {
        erg_physical_address: u8,
        race_lane_number: u8,
    },
    /// Verify race lane (0x0C).
    RaceLaneVerify {
        erg_physical_address: u8,
        race_lane_number: u8,
    },
    /// Set race start parameters (0x0D).
    RaceStartParams {
        start_type: u8,
        count_start: u8,
        ready_tick_count: u32,
        attention_tick_count: u32,
        row_tick_count: u32,
    },
    /// Set erg slave discovery request (0x0E).
    ErgSlaveDiscoveryRequest { starting_erg_slave_address: u8 },
    /// Set boat number (0x0F).
    BoatNumber { boat_number: u8 },
    /// Set erg number (0x10).
    ErgNumber { hw_address: u32, erg_number: u8 },
    /// Set screen state (0x13).
    ScreenState { screen_type: u8, screen_value: u8 },
    /// Configure workout (0x14).
    ConfigureWorkout { programming_mode: u8 },
    /// Set target average watts (0x15).
    TargetAvgWatts { avg_watts: u16 },
    /// Set target calories per hour (0x16).
    TargetCalsPerHr { cals_per_hr: u16 },
    /// Set interval type (0x17).
    IntervalType { interval_type: u8 },
    /// Set workout interval count (0x18).
    WorkoutIntervalCount { interval_count: u8 },
    /// Set display update rate (0x19).
    DisplayUpdateRate { update_rate: u8 },
    /// Set authentication password (0x1A).
    AuthenPassword { hw_address: u32, password: Vec<u8> },
    /// Set tick time (0x1B).
    TickTime { tick_time: u32 },
    /// Set tick time offset (0x1C).
    TickTimeOffset { tick_time_offset: u32 },
    /// Set race data sample ticks (0x1D).
    RaceDataSampleTicks { sample_tick: u32 },
    /// Set race operation type (0x1E).
    RaceOperationType { operation_type: u8 },
    /// Set race status display ticks (0x1F).
    RaceStatusDisplayTicks { display_tick: u32 },
    /// Set race status warning ticks (0x20).
    RaceStatusWarningTicks { warning_tick: u32 },
    /// Set race idle mode parameters (0x21).
    RaceIdleModeParams {
        doze_seconds: u16,
        sleep_seconds: u16,
    },
    /// Set date and time (0x22).
    DateTime {
        hours: u8,
        minutes: u8,
        meridiem: u8,
        month: u8,
        day: u8,
        year: u16,
    },
    /// Set language type (0x23).
    LanguageType { language_type: u8 },
    /// Set WiFi configuration (0x24).
    WifiConfig { config_index: u8, wep_mode: u8 },
    /// Set CPU tick rate (0x25).
    CpuTickRate { cpu_tick_rate: u8 },
    /// Set logcard user (0x26).
    LogCardUser { user_number: u8 },
    /// Set screen error mode (0x27).
    ScreenErrorMode { mode: u8 },
    /// Set cable test mode (0x28).
    CableTest { mode: u8, data: Vec<u8> },
    /// Set user ID (0x29).
    UserId { user_number: u8, user_id: u32 },
    /// Set user profile (0x2A).
    UserProfile {
        user_number: u8,
        user_weight: u16,
        dob_day: u8,
        dob_month: u8,
        dob_year: u16,
        gender: u8,
    },
    /// Set HRM device info (0x2B).
    Hrm {
        mfg_id: u8,
        device_type: u8,
        device_num: u16,
    },
    /// Set race starting physical address (0x2C).
    RaceStartingPhysicalAddress { first_erg_address: u8 },
    /// Set HR belt info (0x2D).
    HrBeltInfo {
        user_number: u8,
        mfg_id: u8,
        device_type: u8,
        belt_id: u16,
    },
    /// Set sensor channel (0x2F).
    SensorChannel {
        rf_frequency: u8,
        rf_period_hz: u16,
        datapage_pattern: u8,
        activity_timeout: u8,
    },
}

impl SetPmCfgCommand {
    /// Returns the proprietary command ID byte.
    pub fn id(&self) -> u8 {
        match self {
            Self::ResetErgNumber => 0xE1,
            Self::WorkoutType { .. } => 0x01,
            Self::WorkoutDuration { .. } => 0x03,
            Self::RestDuration { .. } => 0x04,
            Self::SplitDuration { .. } => 0x05,
            Self::TargetPaceTime { .. } => 0x06,
            Self::RaceType { .. } => 0x09,
            Self::RaceLaneSetup { .. } => 0x0B,
            Self::RaceLaneVerify { .. } => 0x0C,
            Self::RaceStartParams { .. } => 0x0D,
            Self::ErgSlaveDiscoveryRequest { .. } => 0x0E,
            Self::BoatNumber { .. } => 0x0F,
            Self::ErgNumber { .. } => 0x10,
            Self::ScreenState { .. } => 0x13,
            Self::ConfigureWorkout { .. } => 0x14,
            Self::TargetAvgWatts { .. } => 0x15,
            Self::TargetCalsPerHr { .. } => 0x16,
            Self::IntervalType { .. } => 0x17,
            Self::WorkoutIntervalCount { .. } => 0x18,
            Self::DisplayUpdateRate { .. } => 0x19,
            Self::AuthenPassword { .. } => 0x1A,
            Self::TickTime { .. } => 0x1B,
            Self::TickTimeOffset { .. } => 0x1C,
            Self::RaceDataSampleTicks { .. } => 0x1D,
            Self::RaceOperationType { .. } => 0x1E,
            Self::RaceStatusDisplayTicks { .. } => 0x1F,
            Self::RaceStatusWarningTicks { .. } => 0x20,
            Self::RaceIdleModeParams { .. } => 0x21,
            Self::DateTime { .. } => 0x22,
            Self::LanguageType { .. } => 0x23,
            Self::WifiConfig { .. } => 0x24,
            Self::CpuTickRate { .. } => 0x25,
            Self::LogCardUser { .. } => 0x26,
            Self::ScreenErrorMode { .. } => 0x27,
            Self::CableTest { .. } => 0x28,
            Self::UserId { .. } => 0x29,
            Self::UserProfile { .. } => 0x2A,
            Self::Hrm { .. } => 0x2B,
            Self::RaceStartingPhysicalAddress { .. } => 0x2C,
            Self::HrBeltInfo { .. } => 0x2D,
            Self::SensorChannel { .. } => 0x2F,
        }
    }

    /// Returns `true` if this is a short command (no request data).
    pub fn is_short(&self) -> bool {
        self.id() & 0x80 != 0
    }

    /// Encode this sub-command into raw wire bytes.
    pub fn encode(&self) -> Vec<u8> {
        if self.is_short() {
            return vec![self.id()];
        }
        let id = self.id();
        match self {
            Self::WorkoutType { workout_type } => vec![id, 1, *workout_type],
            Self::WorkoutDuration {
                duration_type,
                duration,
            } => {
                let mut v = vec![id, 5, *duration_type];
                v.extend_from_slice(&duration.to_le_bytes());
                v
            }
            Self::RestDuration { duration } => {
                let mut v = vec![id, 2];
                v.extend_from_slice(&duration.to_le_bytes());
                v
            }
            Self::SplitDuration {
                duration_type,
                duration,
            } => {
                let mut v = vec![id, 5, *duration_type];
                v.extend_from_slice(&duration.to_le_bytes());
                v
            }
            Self::TargetPaceTime { pace_time } => {
                let mut v = vec![id, 4];
                v.extend_from_slice(&pace_time.to_le_bytes());
                v
            }
            Self::RaceType { race_type } => vec![id, 1, *race_type],
            Self::RaceLaneSetup {
                erg_physical_address,
                race_lane_number,
            } => {
                vec![id, 2, *erg_physical_address, *race_lane_number]
            }
            Self::RaceLaneVerify {
                erg_physical_address,
                race_lane_number,
            } => {
                vec![id, 2, *erg_physical_address, *race_lane_number]
            }
            Self::RaceStartParams {
                start_type,
                count_start,
                ready_tick_count,
                attention_tick_count,
                row_tick_count,
            } => {
                let mut v = vec![id, 14, *start_type, *count_start];
                v.extend_from_slice(&ready_tick_count.to_le_bytes());
                v.extend_from_slice(&attention_tick_count.to_le_bytes());
                v.extend_from_slice(&row_tick_count.to_le_bytes());
                v
            }
            Self::ErgSlaveDiscoveryRequest {
                starting_erg_slave_address,
            } => {
                vec![id, 1, *starting_erg_slave_address]
            }
            Self::BoatNumber { boat_number } => vec![id, 1, *boat_number],
            Self::ErgNumber {
                hw_address,
                erg_number,
            } => {
                let mut v = vec![id, 5];
                v.extend_from_slice(&hw_address.to_le_bytes());
                v.push(*erg_number);
                v
            }
            Self::ScreenState {
                screen_type,
                screen_value,
            } => {
                vec![id, 2, *screen_type, *screen_value]
            }
            Self::ConfigureWorkout { programming_mode } => vec![id, 1, *programming_mode],
            Self::TargetAvgWatts { avg_watts } => {
                let mut v = vec![id, 2];
                v.extend_from_slice(&avg_watts.to_le_bytes());
                v
            }
            Self::TargetCalsPerHr { cals_per_hr } => {
                let mut v = vec![id, 2];
                v.extend_from_slice(&cals_per_hr.to_le_bytes());
                v
            }
            Self::IntervalType { interval_type } => vec![id, 1, *interval_type],
            Self::WorkoutIntervalCount { interval_count } => vec![id, 1, *interval_count],
            Self::DisplayUpdateRate { update_rate } => vec![id, 1, *update_rate],
            Self::AuthenPassword {
                hw_address,
                password,
            } => {
                let len = 4 + password.len();
                let mut v = vec![id, len as u8];
                v.extend_from_slice(&hw_address.to_le_bytes());
                v.extend_from_slice(password);
                v
            }
            Self::TickTime { tick_time } => {
                let mut v = vec![id, 4];
                v.extend_from_slice(&tick_time.to_le_bytes());
                v
            }
            Self::TickTimeOffset { tick_time_offset } => {
                let mut v = vec![id, 4];
                v.extend_from_slice(&tick_time_offset.to_le_bytes());
                v
            }
            Self::RaceDataSampleTicks { sample_tick } => {
                let mut v = vec![id, 4];
                v.extend_from_slice(&sample_tick.to_le_bytes());
                v
            }
            Self::RaceOperationType { operation_type } => vec![id, 1, *operation_type],
            Self::RaceStatusDisplayTicks { display_tick } => {
                let mut v = vec![id, 4];
                v.extend_from_slice(&display_tick.to_le_bytes());
                v
            }
            Self::RaceStatusWarningTicks { warning_tick } => {
                let mut v = vec![id, 4];
                v.extend_from_slice(&warning_tick.to_le_bytes());
                v
            }
            Self::RaceIdleModeParams {
                doze_seconds,
                sleep_seconds,
            } => {
                let mut v = vec![id, 4];
                v.extend_from_slice(&doze_seconds.to_le_bytes());
                v.extend_from_slice(&sleep_seconds.to_le_bytes());
                v
            }
            Self::DateTime {
                hours,
                minutes,
                meridiem,
                month,
                day,
                year,
            } => {
                let mut v = vec![id, 7, *hours, *minutes, *meridiem, *month, *day];
                v.extend_from_slice(&year.to_le_bytes());
                v
            }
            Self::LanguageType { language_type } => vec![id, 1, *language_type],
            Self::WifiConfig {
                config_index,
                wep_mode,
            } => {
                vec![id, 2, *config_index, *wep_mode]
            }
            Self::CpuTickRate { cpu_tick_rate } => vec![id, 1, *cpu_tick_rate],
            Self::LogCardUser { user_number } => vec![id, 1, *user_number],
            Self::ScreenErrorMode { mode } => vec![id, 1, *mode],
            Self::CableTest { mode, data } => {
                let len = 1 + data.len();
                let mut v = vec![id, len as u8, *mode];
                v.extend_from_slice(data);
                v
            }
            Self::UserId {
                user_number,
                user_id,
            } => {
                let mut v = vec![id, 5, *user_number];
                v.extend_from_slice(&user_id.to_le_bytes());
                v
            }
            Self::UserProfile {
                user_number,
                user_weight,
                dob_day,
                dob_month,
                dob_year,
                gender,
            } => {
                let mut v = vec![id, 8, *user_number];
                v.extend_from_slice(&user_weight.to_le_bytes());
                v.push(*dob_day);
                v.push(*dob_month);
                v.extend_from_slice(&dob_year.to_le_bytes());
                v.push(*gender);
                v
            }
            Self::Hrm {
                mfg_id,
                device_type,
                device_num,
            } => {
                let mut v = vec![id, 4, *mfg_id, *device_type];
                v.extend_from_slice(&device_num.to_le_bytes());
                v
            }
            Self::RaceStartingPhysicalAddress { first_erg_address } => {
                vec![id, 1, *first_erg_address]
            }
            Self::HrBeltInfo {
                user_number,
                mfg_id,
                device_type,
                belt_id,
            } => {
                let mut v = vec![id, 5, *user_number, *mfg_id, *device_type];
                v.extend_from_slice(&belt_id.to_le_bytes());
                v
            }
            Self::SensorChannel {
                rf_frequency,
                rf_period_hz,
                datapage_pattern,
                activity_timeout,
            } => {
                let mut v = vec![id, 5, *rf_frequency];
                v.extend_from_slice(&rf_period_hz.to_le_bytes());
                v.push(*datapage_pattern);
                v.push(*activity_timeout);
                v
            }
            _ => unreachable!(),
        }
    }
}

// =========================================================================
//  SetPmDataCommand — wrapper 0x77 (CSAFE_SETPMDATA_CMD)
// =========================================================================

/// Proprietary set-data commands sent inside `CSAFE_SETPMDATA_CMD` (0x77).
///
/// Short commands (0xD0–0xD3, 0xD7–0xD9) are unit variants.
/// Long commands (0x32–0x3E) carry request fields.
/// Commands marked `not_implemented` in the spec are omitted.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum SetPmDataCommand {
    // --- Short set data ---
    /// Sync distance (0xD0).
    SyncDistance,
    /// Sync stroke pace (0xD1).
    SyncStrokePace,
    /// Sync average heart rate (0xD2).
    SyncAvgHeartRate,
    /// Sync time (0xD3).
    SyncTime,
    /// Sync race tick time (0xD7).
    SyncRaceTickTime,
    /// Sync all data (0xD8).
    SyncDataAll,
    /// Sync rowing active time (0xD9).
    SyncRowingActiveTime,

    // --- Long set data (0x32–0x3E) ---
    /// Set race participant (0x32).
    RaceParticipant { racer_id: u8, racer_name: Vec<u8> },
    /// Set race status (0x33).
    RaceStatus {
        racer1_id: u8,
        racer1_position: u8,
        racer1_delta: u32,
        racer2_id: u8,
        racer2_position: u8,
        racer2_delta: u32,
        racer3_id: u8,
        racer3_position: u8,
        racer3_delta: u32,
        racer4_id: u8,
        racer4_position: u8,
        racer4_delta: u32,
        team_distance: u32,
        mode: u8,
    },
    /// Write logcard memory (0x34).
    LogCardMemory {
        start_address: u32,
        block_length: u8,
        data: Vec<u8>,
    },
    /// Set display string (0x35).
    DisplayString { characters: Vec<u8> },
    /// Set display bitmap (0x36).
    DisplayBitmap {
        bitmap_index: u16,
        block_length: u8,
        data: Vec<u8>,
    },
    /// Set local race participant (0x37).
    LocalRaceParticipant {
        race_type: u8,
        race_length: u32,
        race_participants: u8,
        race_state: u8,
        race_lane: u8,
    },
    /// Set game parameters (0x38).
    GameParams {
        game_type_id: u8,
        workout_duration_time: u32,
        split_duration_time: u32,
        target_pace_time: u32,
        target_avg_watts: u32,
        target_cals_per_hr: u32,
        target_stroke_rate: u8,
    },
    /// Set extended HR belt info (0x39).
    ExtendedHrBeltInfo {
        unused: u8,
        mfg_id: u8,
        device_type: u8,
        belt_id: u32,
    },
    /// Set extended HRM (0x3A).
    ExtendedHrm {
        mfg_id: u8,
        device_type: u8,
        belt_id: u32,
    },
    /// Set LED backlight (0x3B).
    LedBacklight { state: u8, intensity: u8 },
    /// Archive diagnostic log record (0x3C).
    DiagLogRecordArchive { record_type: u8, record_index: u16 },
    /// Set wireless channel config (0x3D).
    WirelessChannelConfig { channel_bitmask: u32 },
    /// Set race control parameters (0x3E).
    RaceControlParams {
        undefined_rest_transition_time: u16,
        undefined_rest_interval: u16,
        race_prompt_bitmap_duration: u32,
        time_cap_duration: u32,
    },
}

impl SetPmDataCommand {
    /// Returns the proprietary command ID byte.
    pub fn id(&self) -> u8 {
        match self {
            Self::SyncDistance => 0xD0,
            Self::SyncStrokePace => 0xD1,
            Self::SyncAvgHeartRate => 0xD2,
            Self::SyncTime => 0xD3,
            Self::SyncRaceTickTime => 0xD7,
            Self::SyncDataAll => 0xD8,
            Self::SyncRowingActiveTime => 0xD9,
            Self::RaceParticipant { .. } => 0x32,
            Self::RaceStatus { .. } => 0x33,
            Self::LogCardMemory { .. } => 0x34,
            Self::DisplayString { .. } => 0x35,
            Self::DisplayBitmap { .. } => 0x36,
            Self::LocalRaceParticipant { .. } => 0x37,
            Self::GameParams { .. } => 0x38,
            Self::ExtendedHrBeltInfo { .. } => 0x39,
            Self::ExtendedHrm { .. } => 0x3A,
            Self::LedBacklight { .. } => 0x3B,
            Self::DiagLogRecordArchive { .. } => 0x3C,
            Self::WirelessChannelConfig { .. } => 0x3D,
            Self::RaceControlParams { .. } => 0x3E,
        }
    }

    /// Returns `true` if this is a short command (no request data).
    pub fn is_short(&self) -> bool {
        self.id() & 0x80 != 0
    }

    /// Encode this sub-command into raw wire bytes.
    pub fn encode(&self) -> Vec<u8> {
        if self.is_short() {
            return vec![self.id()];
        }
        let id = self.id();
        match self {
            Self::RaceParticipant {
                racer_id,
                racer_name,
            } => {
                let len = 1 + racer_name.len();
                let mut v = vec![id, len as u8, *racer_id];
                v.extend_from_slice(racer_name);
                v
            }
            Self::RaceStatus {
                racer1_id,
                racer1_position,
                racer1_delta,
                racer2_id,
                racer2_position,
                racer2_delta,
                racer3_id,
                racer3_position,
                racer3_delta,
                racer4_id,
                racer4_position,
                racer4_delta,
                team_distance,
                mode,
            } => {
                let mut v = vec![id, 29];
                for (rid, pos, delta) in [
                    (racer1_id, racer1_position, racer1_delta),
                    (racer2_id, racer2_position, racer2_delta),
                    (racer3_id, racer3_position, racer3_delta),
                    (racer4_id, racer4_position, racer4_delta),
                ] {
                    v.push(*rid);
                    v.push(*pos);
                    v.extend_from_slice(&delta.to_le_bytes());
                }
                v.extend_from_slice(&team_distance.to_le_bytes());
                v.push(*mode);
                v
            }
            Self::LogCardMemory {
                start_address,
                block_length,
                data,
            } => {
                let len = 5 + data.len();
                let mut v = vec![id, len as u8];
                v.extend_from_slice(&start_address.to_le_bytes());
                v.push(*block_length);
                v.extend_from_slice(data);
                v
            }
            Self::DisplayString { characters } => {
                let mut v = vec![id, characters.len() as u8];
                v.extend_from_slice(characters);
                v
            }
            Self::DisplayBitmap {
                bitmap_index,
                block_length,
                data,
            } => {
                let len = 3 + data.len();
                let mut v = vec![id, len as u8];
                v.extend_from_slice(&bitmap_index.to_le_bytes());
                v.push(*block_length);
                v.extend_from_slice(data);
                v
            }
            Self::LocalRaceParticipant {
                race_type,
                race_length,
                race_participants,
                race_state,
                race_lane,
            } => {
                let mut v = vec![id, 8, *race_type];
                v.extend_from_slice(&race_length.to_le_bytes());
                v.push(*race_participants);
                v.push(*race_state);
                v.push(*race_lane);
                v
            }
            Self::GameParams {
                game_type_id,
                workout_duration_time,
                split_duration_time,
                target_pace_time,
                target_avg_watts,
                target_cals_per_hr,
                target_stroke_rate,
            } => {
                let mut v = vec![id, 22, *game_type_id];
                v.extend_from_slice(&workout_duration_time.to_le_bytes());
                v.extend_from_slice(&split_duration_time.to_le_bytes());
                v.extend_from_slice(&target_pace_time.to_le_bytes());
                v.extend_from_slice(&target_avg_watts.to_le_bytes());
                v.extend_from_slice(&target_cals_per_hr.to_le_bytes());
                v.push(*target_stroke_rate);
                v
            }
            Self::ExtendedHrBeltInfo {
                unused,
                mfg_id,
                device_type,
                belt_id,
            } => {
                let mut v = vec![id, 7, *unused, *mfg_id, *device_type];
                v.extend_from_slice(&belt_id.to_le_bytes());
                v
            }
            Self::ExtendedHrm {
                mfg_id,
                device_type,
                belt_id,
            } => {
                let mut v = vec![id, 6, *mfg_id, *device_type];
                v.extend_from_slice(&belt_id.to_le_bytes());
                v
            }
            Self::LedBacklight { state, intensity } => vec![id, 2, *state, *intensity],
            Self::DiagLogRecordArchive {
                record_type,
                record_index,
            } => {
                let mut v = vec![id, 3, *record_type];
                v.extend_from_slice(&record_index.to_le_bytes());
                v
            }
            Self::WirelessChannelConfig { channel_bitmask } => {
                let mut v = vec![id, 4];
                v.extend_from_slice(&channel_bitmask.to_le_bytes());
                v
            }
            Self::RaceControlParams {
                undefined_rest_transition_time,
                undefined_rest_interval,
                race_prompt_bitmap_duration,
                time_cap_duration,
            } => {
                let mut v = vec![id, 12];
                v.extend_from_slice(&undefined_rest_transition_time.to_le_bytes());
                v.extend_from_slice(&undefined_rest_interval.to_le_bytes());
                v.extend_from_slice(&race_prompt_bitmap_duration.to_le_bytes());
                v.extend_from_slice(&time_cap_duration.to_le_bytes());
                v
            }
            _ => unreachable!(),
        }
    }
}

// =========================================================================
//  SetUserCfg1Command — wrapper 0x1A (CSAFE_SETUSERCFG1_CMD)
// =========================================================================

/// Restricted proprietary commands sent inside `CSAFE_SETUSERCFG1_CMD` (0x1A).
///
/// This is a limited subset of `long_set_config` commands that are permitted
/// through the public `SETUSERCFG1` wrapper used by apps for workout programming.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum SetUserCfg1Command {
    /// Set workout type (0x01).
    WorkoutType { workout_type: u8 },
    /// Set workout duration (0x03).
    WorkoutDuration { duration_type: u8, duration: u32 },
    /// Set split duration (0x05).
    SplitDuration { duration_type: u8, duration: u32 },
    /// Configure workout (0x14).
    ConfigureWorkout { programming_mode: u8 },
    /// Set interval type (0x17).
    IntervalType { interval_type: u8 },
    /// Set workout interval count (0x18).
    WorkoutIntervalCount { interval_count: u8 },
}

impl SetUserCfg1Command {
    /// Returns the proprietary command ID byte.
    pub fn id(&self) -> u8 {
        match self {
            Self::WorkoutType { .. } => 0x01,
            Self::WorkoutDuration { .. } => 0x03,
            Self::SplitDuration { .. } => 0x05,
            Self::ConfigureWorkout { .. } => 0x14,
            Self::IntervalType { .. } => 0x17,
            Self::WorkoutIntervalCount { .. } => 0x18,
        }
    }

    /// Returns `true` if this is a short command (no request data).
    pub fn is_short(&self) -> bool {
        false // All SetUserCfg1 commands are long
    }

    /// Encode this sub-command into raw wire bytes.
    pub fn encode(&self) -> Vec<u8> {
        let id = self.id();
        match self {
            Self::WorkoutType { workout_type } => vec![id, 1, *workout_type],
            Self::WorkoutDuration {
                duration_type,
                duration,
            } => {
                let mut v = vec![id, 5, *duration_type];
                v.extend_from_slice(&duration.to_le_bytes());
                v
            }
            Self::SplitDuration {
                duration_type,
                duration,
            } => {
                let mut v = vec![id, 5, *duration_type];
                v.extend_from_slice(&duration.to_le_bytes());
                v
            }
            Self::ConfigureWorkout { programming_mode } => vec![id, 1, *programming_mode],
            Self::IntervalType { interval_type } => vec![id, 1, *interval_type],
            Self::WorkoutIntervalCount { interval_count } => vec![id, 1, *interval_count],
        }
    }
}
