//! CSAFE response parsing: status byte decoding and command response extraction.
//!
//! A CSAFE response frame's contents (after frame parsing and unstuffing) begin
//! with a single status byte followed by zero or more individual command
//! response blocks.  Each block echoes the command ID, a byte count, and data.
//!
//! Reference: protocol.yaml §response_format (Figures 5-6, Tables 8-9).

use std::fmt;

// ── Error type ────────────────────────────────────────────────────────

/// Errors that can occur while parsing a CSAFE response.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum ResponseError {
    /// The response frame contents are empty (no status byte).
    Empty,
    /// The status byte contains an unknown server state value.
    InvalidServerState { value: u8 },
    /// A command response block is truncated (missing byte count).
    TruncatedCommand { position: usize },
    /// A command response claims more data bytes than remain in the buffer.
    InsufficientData {
        command_id: u8,
        expected: usize,
        available: usize,
    },
}

impl fmt::Display for ResponseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => write!(f, "response frame contents are empty"),
            Self::InvalidServerState { value } => {
                write!(f, "invalid server state value: 0x{value:02X}")
            }
            Self::TruncatedCommand { position } => {
                write!(f, "truncated command response at byte {position}")
            }
            Self::InsufficientData {
                command_id,
                expected,
                available,
            } => {
                write!(
                    f,
                    "command 0x{command_id:02X} expects {expected} data bytes, only {available} available"
                )
            }
        }
    }
}

impl std::error::Error for ResponseError {}

// ── Status byte types ─────────────────────────────────────────────────

/// Previous frame status reported in the response status byte (bits 5-4).
///
/// Indicates how the PM processed the *previous* request frame.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum PrevFrameStatus {
    /// Previous frame accepted and processed.
    Ok = 0,
    /// Previous frame rejected (invalid command for current state).
    Reject = 1,
    /// Previous frame was malformed or had bad checksum.
    Bad = 2,
    /// PM was not ready to process the previous frame.
    NotReady = 3,
}

impl fmt::Display for PrevFrameStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Debug::fmt(self, f)
    }
}

/// PM state machine state reported in the response status byte (bits 3-0).
///
/// Reference: protocol.yaml §pm_state_machine, Table 9.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
#[non_exhaustive]
pub enum ServerState {
    /// Error condition.
    Error = 0x00,
    /// Ready — powered on, waiting.
    Ready = 0x01,
    /// Idle — no user interaction.
    Idle = 0x02,
    /// Have ID — user ID assigned.
    HaveId = 0x03,
    // 0x04 is not defined in the spec.
    /// In Use — workout active.
    InUse = 0x05,
    /// Paused.
    Pause = 0x06,
    /// Finished — workout complete.
    Finish = 0x07,
    /// Manual mode.
    Manual = 0x08,
    /// Offline.
    Offline = 0x09,
}

impl TryFrom<u8> for ServerState {
    type Error = ResponseError;

    fn try_from(value: u8) -> Result<Self, <Self as TryFrom<u8>>::Error> {
        match value {
            0x00 => Ok(Self::Error),
            0x01 => Ok(Self::Ready),
            0x02 => Ok(Self::Idle),
            0x03 => Ok(Self::HaveId),
            0x05 => Ok(Self::InUse),
            0x06 => Ok(Self::Pause),
            0x07 => Ok(Self::Finish),
            0x08 => Ok(Self::Manual),
            0x09 => Ok(Self::Offline),
            _ => Err(ResponseError::InvalidServerState { value }),
        }
    }
}

impl fmt::Display for ServerState {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Debug::fmt(self, f)
    }
}

// ── Decoded types ─────────────────────────────────────────────────────

/// Decoded CSAFE response status byte.
///
/// Layout (protocol.yaml §response_format.status_byte, Table 9):
/// ```text
///   bit 7      : frame_toggle (alternates 0/1 per frame)
///   bit 6      : reserved (ignored)
///   bits 5-4   : previous_frame_status (Ok/Reject/Bad/NotReady)
///   bits 3-0   : server_state (PM state machine)
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct StatusByte {
    /// Toggles between 0 and 1 on alternate response frames.
    pub frame_toggle: bool,
    /// How the PM processed the *previous* request frame.
    pub prev_frame_status: PrevFrameStatus,
    /// Current PM state machine state.
    pub server_state: ServerState,
}

/// A single command response block within a CSAFE response frame.
///
/// Each block echoes the command identifier that generated it, followed
/// by a byte count and data payload (protocol.yaml §individual_response).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommandResponse {
    /// Echo of the command ID that generated this response.
    pub command_id: u8,
    /// Response data bytes (may be empty for commands with no return data).
    pub data: Vec<u8>,
}

/// A fully parsed CSAFE response (status byte + command response blocks).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Response {
    /// Decoded status byte (first byte of the response frame contents).
    pub status: StatusByte,
    /// Zero or more individual command responses, in request order.
    pub commands: Vec<CommandResponse>,
}

// ── Parsing ───────────────────────────────────────────────────────────

/// Parse the CSAFE status byte.
///
/// Extracts frame toggle (bit 7), previous frame status (bits 5-4),
/// and server state (bits 3-0) from a single byte.
///
/// # Errors
///
/// Returns [`ResponseError::InvalidServerState`] if the low nibble
/// does not map to a known [`ServerState`] variant.
pub fn parse_status_byte(byte: u8) -> Result<StatusByte, ResponseError> {
    let frame_toggle = byte & 0x80 != 0;
    let prev_frame_status = match (byte & 0x30) >> 4 {
        0 => PrevFrameStatus::Ok,
        1 => PrevFrameStatus::Reject,
        2 => PrevFrameStatus::Bad,
        3 => PrevFrameStatus::NotReady,
        _ => unreachable!(),
    };
    let server_state = ServerState::try_from(byte & 0x0F)?;
    Ok(StatusByte {
        frame_toggle,
        prev_frame_status,
        server_state,
    })
}

/// Parse a sequence of command response blocks from a byte slice.
///
/// Each block has the structure: `[command_id] [byte_count] [data...]`.
/// This is used both for top-level response parsing and for extracting
/// sub-responses from within proprietary wrapper command data.
///
/// # Errors
///
/// Returns [`ResponseError::TruncatedCommand`] if a block is missing
/// its byte count, or [`ResponseError::InsufficientData`] if the
/// claimed data length exceeds the remaining bytes.
pub fn parse_command_responses(data: &[u8]) -> Result<Vec<CommandResponse>, ResponseError> {
    let mut commands = Vec::new();
    let mut pos = 0;

    while pos < data.len() {
        let command_id = data[pos];
        pos += 1;

        if pos >= data.len() {
            return Err(ResponseError::TruncatedCommand { position: pos - 1 });
        }

        let byte_count = data[pos] as usize;
        pos += 1;

        if pos + byte_count > data.len() {
            return Err(ResponseError::InsufficientData {
                command_id,
                expected: byte_count,
                available: data.len() - pos,
            });
        }

        let cmd_data = data[pos..pos + byte_count].to_vec();
        pos += byte_count;

        commands.push(CommandResponse {
            command_id,
            data: cmd_data,
        });
    }

    Ok(commands)
}

/// Parse a complete CSAFE response from frame contents.
///
/// The `contents` argument is the raw (unstuffed) payload returned by
/// [`parse_standard_frame`](crate::framing::parse_standard_frame) or
/// [`parse_extended_frame`](crate::framing::parse_extended_frame).
///
/// # Wire format
///
/// ```text
///   [status_byte] [cmd_id byte_count data...]*
/// ```
///
/// # Errors
///
/// - [`ResponseError::Empty`] if `contents` is empty.
/// - [`ResponseError::InvalidServerState`] if the status byte has an
///   unknown state value.
/// - [`ResponseError::TruncatedCommand`] or [`ResponseError::InsufficientData`]
///   if command response blocks are malformed.
pub fn parse_response(contents: &[u8]) -> Result<Response, ResponseError> {
    if contents.is_empty() {
        return Err(ResponseError::Empty);
    }

    let status = parse_status_byte(contents[0])?;
    let commands = parse_command_responses(&contents[1..])?;

    Ok(Response { status, commands })
}

#[cfg(test)]
mod tests;
