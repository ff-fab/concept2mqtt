// CSAFE frame-level primitives: byte stuffing, checksum, frame building,
// and frame parsing.
//
// Byte stuffing (protocol.yaml §byte_stuffing, Table 6) ensures the four
// flag bytes 0xF0–0xF3 never appear inside frame contents or the checksum.
// Each reserved byte is replaced by a two-byte escape sequence:
// [0xF3, byte − 0xF0].
//
// Checksum (protocol.yaml §checksum) is a single-byte XOR over the
// (unstuffed) frame contents, excluding start/stop flags and extended-frame
// addresses.  The checksum byte itself is subject to byte-stuffing.
//
// Standard frame (protocol.yaml §standard, Figure 1) layout:
//   [0xF1]  [stuffed contents]  [stuffed checksum]  [0xF2]
// The total wire size (including flags) must not exceed 120 bytes.
//
// Parsing (protocol.yaml §error_recovery): if a start or stop byte is
// missed, the frame is discarded and resynchronisation occurs at the next
// frame boundary.  No ACK/NAK at the frame level.

// ── Flag constants ──────────────────────────────────────────────────────

/// Extended frame start flag.
pub const EXTENDED_START: u8 = 0xF0;
/// Standard frame start flag.
pub const STANDARD_START: u8 = 0xF1;
/// Frame stop flag (both standard and extended).
pub const STOP: u8 = 0xF2;
/// Byte-stuffing escape marker.
pub const STUFF_MARKER: u8 = 0xF3;

/// Inclusive range of bytes that must be escaped.
const STUFF_RANGE: std::ops::RangeInclusive<u8> = EXTENDED_START..=STUFF_MARKER;

// ── Error types ─────────────────────────────────────────────────────────

/// Errors that can occur while unstuffing a CSAFE byte stream.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StuffingError {
    /// An escape marker (0xF3) appeared as the last byte with no offset following.
    TruncatedEscape { position: usize },
    /// The byte following an escape marker was outside the valid range 0x00–0x03.
    InvalidOffset { position: usize, offset: u8 },
}

impl std::fmt::Display for StuffingError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            StuffingError::TruncatedEscape { position } => {
                write!(f, "truncated escape at byte {position}")
            }
            StuffingError::InvalidOffset { position, offset } => {
                write!(f, "invalid escape offset 0x{offset:02X} at byte {position}")
            }
        }
    }
}

// ── Public API ──────────────────────────────────────────────────────────

/// Replace every byte in the reserved range [0xF0, 0xF3] with its
/// two-byte escape sequence `[0xF3, byte − 0xF0]`.
pub fn stuff_bytes(data: &[u8]) -> Vec<u8> {
    // Worst case: every byte is stuffed → 2× input length.
    let mut out = Vec::with_capacity(data.len().saturating_mul(2));
    for &b in data {
        if STUFF_RANGE.contains(&b) {
            out.push(STUFF_MARKER);
            out.push(b - EXTENDED_START);
        } else {
            out.push(b);
        }
    }
    out
}

/// Reverse byte stuffing: every `[0xF3, offset]` pair is replaced by
/// `0xF0 + offset`.
///
/// Returns an error if the stream contains a truncated escape (0xF3 at
/// end-of-input) or an offset outside 0x00–0x03.
pub fn unstuff_bytes(data: &[u8]) -> Result<Vec<u8>, StuffingError> {
    let mut out = Vec::with_capacity(data.len());
    let mut i = 0;
    while i < data.len() {
        if data[i] == STUFF_MARKER {
            let Some(&offset) = data.get(i + 1) else {
                return Err(StuffingError::TruncatedEscape { position: i });
            };
            if offset > 0x03 {
                return Err(StuffingError::InvalidOffset {
                    position: i + 1,
                    offset,
                });
            }
            out.push(EXTENDED_START + offset);
            i += 2;
        } else {
            out.push(data[i]);
            i += 1;
        }
    }
    Ok(out)
}

// ── Checksum ────────────────────────────────────────────────────────────

/// Compute the CSAFE checksum: byte-by-byte XOR of `data`.
///
/// `data` should be the raw (unstuffed) frame contents — excluding
/// start/stop flags and, for extended frames, the address bytes.
/// An empty slice yields `0x00`.
pub fn compute_checksum(data: &[u8]) -> u8 {
    data.iter().fold(0u8, |acc, &b| acc ^ b)
}

/// Check whether `expected` matches the XOR checksum of `data`.
pub fn validate_checksum(data: &[u8], expected: u8) -> bool {
    compute_checksum(data) == expected
}

// ── Frame building ──────────────────────────────────────────────────────

/// Maximum total frame size on the wire (start + stuffed body + stuffed
/// checksum + stop), per protocol.yaml §constraints.
pub const MAX_FRAME_SIZE: usize = 120;

/// Overhead beyond the stuffed contents: start flag (1) + stop flag (1).
/// The stuffed checksum is variable (1 or 2 bytes) so it's accounted for
/// dynamically.
const FRAME_ENVELOPE: usize = 2; // start + stop

/// Errors that can occur when building a CSAFE frame.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FrameError {
    /// The resulting frame would exceed the 120-byte protocol limit.
    TooLarge {
        /// Actual wire size that would have been produced.
        actual: usize,
    },
}

impl std::fmt::Display for FrameError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FrameError::TooLarge { actual } => {
                write!(
                    f,
                    "frame size {actual} bytes exceeds {MAX_FRAME_SIZE}-byte limit"
                )
            }
        }
    }
}

/// Build a standard CSAFE frame from raw (unstuffed) `contents`.
///
/// Returns the complete wire-format frame:
/// `[0xF1] [stuffed contents] [stuffed checksum] [0xF2]`
///
/// # Errors
///
/// Returns [`FrameError::TooLarge`] if the resulting frame would exceed
/// the 120-byte protocol limit.
pub fn build_standard_frame(contents: &[u8]) -> Result<Vec<u8>, FrameError> {
    // Fast reject: raw contents alone exceed the frame limit, so the
    // stuffed frame (which is >= contents) certainly will too.  Avoids
    // an unnecessary O(n) allocation for oversized inputs.
    if contents.len() > MAX_FRAME_SIZE {
        return Err(FrameError::TooLarge {
            actual: FRAME_ENVELOPE + contents.len() + 1,
        });
    }

    let stuffed_contents = stuff_bytes(contents);
    let checksum = compute_checksum(contents);
    let stuffed_checksum = stuff_bytes(&[checksum]);

    let total = FRAME_ENVELOPE + stuffed_contents.len() + stuffed_checksum.len();
    if total > MAX_FRAME_SIZE {
        return Err(FrameError::TooLarge { actual: total });
    }

    let mut frame = Vec::with_capacity(total);
    frame.push(STANDARD_START);
    frame.extend_from_slice(&stuffed_contents);
    frame.extend_from_slice(&stuffed_checksum);
    frame.push(STOP);
    Ok(frame)
}

// ── Frame parsing ───────────────────────────────────────────────────────

/// Errors that can occur when parsing a CSAFE frame from wire bytes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    /// The first byte is not the standard start flag (0xF1).
    MissingStartFlag { actual: u8 },
    /// The last byte is not the stop flag (0xF2).
    MissingStopFlag { actual: u8 },
    /// The frame is too short to contain even a checksum (start + stop only).
    EmptyFrame,
    /// The wire frame exceeds the 120-byte protocol limit.
    TooLarge {
        /// Actual frame size in bytes.
        actual: usize,
    },
    /// Byte-unstuffing failed inside the frame body.
    Unstuffing(StuffingError),
    /// The checksum computed over the contents does not match the frame's
    /// checksum byte.
    BadChecksum { expected: u8, actual: u8 },
}

impl std::fmt::Display for ParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ParseError::MissingStartFlag { actual } => {
                write!(f, "expected start flag 0xF1, got 0x{actual:02X}")
            }
            ParseError::MissingStopFlag { actual } => {
                write!(f, "expected stop flag 0xF2, got 0x{actual:02X}")
            }
            ParseError::EmptyFrame => write!(f, "frame contains no data or checksum"),
            ParseError::TooLarge { actual } => {
                write!(
                    f,
                    "frame size {actual} bytes exceeds {MAX_FRAME_SIZE}-byte limit"
                )
            }
            ParseError::Unstuffing(e) => write!(f, "unstuffing error: {e}"),
            ParseError::BadChecksum { expected, actual } => {
                write!(
                    f,
                    "checksum mismatch: frame has 0x{expected:02X}, computed 0x{actual:02X}"
                )
            }
        }
    }
}

impl From<StuffingError> for ParseError {
    fn from(e: StuffingError) -> Self {
        ParseError::Unstuffing(e)
    }
}

/// Parse a standard CSAFE frame from wire bytes, returning the raw
/// (unstuffed) frame contents.
///
/// Expects the full frame including start/stop flags:
/// `[0xF1] [stuffed body + stuffed checksum] [0xF2]`
///
/// Steps:
/// 1. Validate start flag (0xF1) and stop flag (0xF2).
/// 2. Unstuff the body between the flags.
/// 3. Split the last byte as the checksum.
/// 4. Validate the checksum against the contents.
/// 5. Return the contents (without the checksum byte).
///
/// # Errors
///
/// Returns [`ParseError`] for missing flags, empty frames, unstuffing
/// failures, or checksum mismatches.
pub fn parse_standard_frame(frame: &[u8]) -> Result<Vec<u8>, ParseError> {
    // At minimum we need: start(1) + checksum(1..2 stuffed) + stop(1) = 3 bytes.
    // But we check structurally instead.
    if frame.is_empty() {
        return Err(ParseError::EmptyFrame);
    }

    if frame.len() > MAX_FRAME_SIZE {
        return Err(ParseError::TooLarge {
            actual: frame.len(),
        });
    }

    let start = frame[0];
    if start != STANDARD_START {
        return Err(ParseError::MissingStartFlag { actual: start });
    }

    let stop = *frame.last().unwrap(); // safe: frame is non-empty
    if stop != STOP {
        return Err(ParseError::MissingStopFlag { actual: stop });
    }

    // Body sits between start and stop flags.
    let stuffed_body = &frame[1..frame.len() - 1];

    // Unstuff the body (contents + checksum together).
    let unstuffed = unstuff_bytes(stuffed_body)?; // ? uses From<StuffingError>

    // The last unstuffed byte is the checksum; everything before it is contents.
    if unstuffed.is_empty() {
        return Err(ParseError::EmptyFrame);
    }
    let (contents, checksum_slice) = unstuffed.split_at(unstuffed.len() - 1);
    let frame_checksum = checksum_slice[0];

    let computed = compute_checksum(contents);
    if computed != frame_checksum {
        return Err(ParseError::BadChecksum {
            expected: frame_checksum,
            actual: computed,
        });
    }

    Ok(contents.to_vec())
}

// ── Unit tests ──────────────────────────────────────────────────────────

#[cfg(test)]
mod tests;
