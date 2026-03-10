use super::proprietary::*;

/// A public CSAFE command that can be placed in a standard frame.
///
/// Short commands (0x80–0xFF) carry no data — they are single-byte on the wire.
/// Long commands (0x00–0x7F) carry typed data fields per the CSAFE spec.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum Command {
    // === State transition (short, 0x80–0x88) ===
    /// Get PM status (0x80).
    GetStatus,
    /// Reset PM (0x81).
    Reset,
    /// Transition to idle state (0x82).
    GoIdle,
    /// Transition to "have ID" state (0x83).
    GoHaveId,
    /// Transition to "in use" state (0x85).
    GoInUse,
    /// Transition to "finished" state (0x86).
    GoFinished,
    /// Transition to "ready" state (0x87).
    GoReady,
    /// Report bad ID (0x88).
    BadId,

    // === Identification (short, 0x91–0x94) ===
    /// Get firmware version (0x91).
    GetVersion,
    /// Get unit ID (0x92).
    GetId,
    /// Get display units (0x93).
    GetUnits,
    /// Get serial number (0x94).
    GetSerial,

    // === Odometer/Error (short, 0x9B–0x9C) ===
    /// Get odometer value (0x9B).
    GetOdometer,
    /// Get error code (0x9C).
    GetErrorCode,

    // === Workout data (short, 0xA0–0xAB) ===
    /// Get total work time (0xA0).
    GetTWork,
    /// Get horizontal distance (0xA1).
    GetHorizontal,
    /// Get calories burned (0xA3).
    GetCalories,
    /// Get current program (0xA4).
    GetProgram,
    /// Get current pace (0xA6).
    GetPace,
    /// Get stroke cadence (0xA7).
    GetCadence,
    /// Get user info (0xAB).
    GetUserInfo,

    // === Heart rate / Power (short) ===
    /// Get heart rate (0xB0).
    GetHeartRate,
    /// Get power output (0xB4).
    GetPower,

    // === Configuration (long, 0x01–0x13) ===
    /// Configure auto-upload (0x01).
    AutoUpload {
        /// Upload configuration bits.
        configuration: u8,
    },
    /// Set ID digit count (0x10).
    IdDigits {
        /// Number of digits.
        count: u8,
    },
    /// Set time of day (0x11).
    SetTime {
        /// Hour (0–23).
        hour: u8,
        /// Minute (0–59).
        minute: u8,
        /// Second (0–59).
        second: u8,
    },
    /// Set date (0x12).
    SetDate {
        /// Year offset.
        year: u8,
        /// Month (1–12).
        month: u8,
        /// Day (1–31).
        day: u8,
    },
    /// Set communication timeout (0x13).
    SetTimeout {
        /// Timeout value.
        timeout: u8,
    },

    // === Workout setup (long, 0x20–0x34) ===
    /// Set total work time target (0x20).
    SetTWork {
        /// Hours.
        hours: u8,
        /// Minutes.
        minutes: u8,
        /// Seconds.
        seconds: u8,
    },
    /// Set horizontal distance target (0x21).
    SetHorizontal {
        /// Distance low byte.
        distance_lsb: u8,
        /// Distance high byte.
        distance_msb: u8,
        /// Distance units.
        units: u8,
    },
    /// Set calorie target (0x23).
    SetCalories {
        /// Calories low byte.
        calories_lsb: u8,
        /// Calories high byte.
        calories_msb: u8,
    },
    /// Set workout program (0x24).
    SetProgram {
        /// Program number.
        program: u8,
        /// Reserved/unused byte.
        unused: u8,
    },
    /// Set power target (0x34).
    SetPower {
        /// Watts low byte.
        watts_lsb: u8,
        /// Watts high byte.
        watts_msb: u8,
        /// Power units.
        units: u8,
    },

    // === Capabilities (long, 0x70) ===
    /// Query device capabilities (0x70).
    GetCaps {
        /// Capability code to query.
        capability_code: u8,
    },

    // === PM-specific wrappers (long, carry typed sub-commands) ===
    /// Wrapper for limited proprietary commands (0x1A).
    SetUserCfg1 { commands: Vec<SetUserCfg1Command> },
    /// Wrapper for proprietary set-configuration commands (0x76).
    SetPmCfg { commands: Vec<SetPmCfgCommand> },
    /// Wrapper for proprietary set-data commands (0x77).
    SetPmData { commands: Vec<SetPmDataCommand> },
    /// Wrapper for proprietary get-configuration commands (0x7E).
    GetPmCfg { commands: Vec<GetPmCfgCommand> },
    /// Wrapper for proprietary get-data commands (0x7F).
    GetPmData { commands: Vec<GetPmDataCommand> },
}

impl Command {
    /// Returns the CSAFE command ID byte for this command.
    pub fn id(&self) -> u8 {
        match self {
            // State transition
            Self::GetStatus => 0x80,
            Self::Reset => 0x81,
            Self::GoIdle => 0x82,
            Self::GoHaveId => 0x83,
            Self::GoInUse => 0x85,
            Self::GoFinished => 0x86,
            Self::GoReady => 0x87,
            Self::BadId => 0x88,
            // Identification
            Self::GetVersion => 0x91,
            Self::GetId => 0x92,
            Self::GetUnits => 0x93,
            Self::GetSerial => 0x94,
            // Odometer/Error
            Self::GetOdometer => 0x9B,
            Self::GetErrorCode => 0x9C,
            // Workout data
            Self::GetTWork => 0xA0,
            Self::GetHorizontal => 0xA1,
            Self::GetCalories => 0xA3,
            Self::GetProgram => 0xA4,
            Self::GetPace => 0xA6,
            Self::GetCadence => 0xA7,
            Self::GetUserInfo => 0xAB,
            // Heart rate / Power
            Self::GetHeartRate => 0xB0,
            Self::GetPower => 0xB4,
            // Configuration
            Self::AutoUpload { .. } => 0x01,
            Self::IdDigits { .. } => 0x10,
            Self::SetTime { .. } => 0x11,
            Self::SetDate { .. } => 0x12,
            Self::SetTimeout { .. } => 0x13,
            // Workout setup
            Self::SetTWork { .. } => 0x20,
            Self::SetHorizontal { .. } => 0x21,
            Self::SetCalories { .. } => 0x23,
            Self::SetProgram { .. } => 0x24,
            Self::SetPower { .. } => 0x34,
            // Capabilities
            Self::GetCaps { .. } => 0x70,
            // PM wrappers
            Self::SetUserCfg1 { .. } => 0x1A,
            Self::SetPmCfg { .. } => 0x76,
            Self::SetPmData { .. } => 0x77,
            Self::GetPmCfg { .. } => 0x7E,
            Self::GetPmData { .. } => 0x7F,
        }
    }

    /// Returns `true` if this is a short command (0x80–0xFF, no data bytes).
    pub fn is_short(&self) -> bool {
        self.id() & 0x80 != 0
    }

    /// Encode this command into raw wire bytes (without framing or byte-stuffing).
    pub fn encode(&self) -> Vec<u8> {
        if self.is_short() {
            return vec![self.id()];
        }

        match self {
            Self::AutoUpload { configuration } => vec![0x01, 0x01, *configuration],
            Self::IdDigits { count } => vec![0x10, 0x01, *count],
            Self::SetTime {
                hour,
                minute,
                second,
            } => vec![0x11, 0x03, *hour, *minute, *second],
            Self::SetDate { year, month, day } => vec![0x12, 0x03, *year, *month, *day],
            Self::SetTimeout { timeout } => vec![0x13, 0x01, *timeout],
            Self::SetTWork {
                hours,
                minutes,
                seconds,
            } => {
                vec![0x20, 0x03, *hours, *minutes, *seconds]
            }
            Self::SetHorizontal {
                distance_lsb,
                distance_msb,
                units,
            } => {
                vec![0x21, 0x03, *distance_lsb, *distance_msb, *units]
            }
            Self::SetCalories {
                calories_lsb,
                calories_msb,
            } => {
                vec![0x23, 0x02, *calories_lsb, *calories_msb]
            }
            Self::SetProgram { program, unused } => vec![0x24, 0x02, *program, *unused],
            Self::SetPower {
                watts_lsb,
                watts_msb,
                units,
            } => {
                vec![0x34, 0x03, *watts_lsb, *watts_msb, *units]
            }
            Self::GetCaps { capability_code } => vec![0x70, 0x01, *capability_code],

            // Wrapper commands: encode sub-commands and prepend opcode + total length.
            Self::SetUserCfg1 { commands } => {
                encode_wrapper(0x1A, commands, SetUserCfg1Command::encode)
            }
            Self::SetPmCfg { commands } => encode_wrapper(0x76, commands, SetPmCfgCommand::encode),
            Self::SetPmData { commands } => {
                encode_wrapper(0x77, commands, SetPmDataCommand::encode)
            }
            Self::GetPmCfg { commands } => encode_wrapper(0x7E, commands, GetPmCfgCommand::encode),
            Self::GetPmData { commands } => {
                encode_wrapper(0x7F, commands, GetPmDataCommand::encode)
            }

            // Short commands already handled above; this is unreachable.
            _ => unreachable!(),
        }
    }
}

/// Helper: encode a wrapper command (opcode + byte-count + concatenated sub-commands).
fn encode_wrapper<T>(opcode: u8, cmds: &[T], encode_fn: fn(&T) -> Vec<u8>) -> Vec<u8> {
    let payload: Vec<u8> = cmds.iter().flat_map(encode_fn).collect();
    let mut out = vec![opcode, payload.len() as u8];
    out.extend(payload);
    out
}
