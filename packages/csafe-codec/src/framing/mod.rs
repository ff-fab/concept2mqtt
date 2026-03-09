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

// ── Address constants (extended frames) ──────────────────────────────────

/// PC host (primary device) address.
pub const ADDR_PC_HOST: u8 = 0x00;
/// Default secondary device address.
pub const ADDR_DEFAULT_SECONDARY: u8 = 0xFD;
/// Reserved for future expansion.
pub const ADDR_RESERVED: u8 = 0xFE;
/// Broadcast address — accepted by all secondaries.
pub const ADDR_BROADCAST: u8 = 0xFF;

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
    /// The first byte is not the expected start flag.
    MissingStartFlag { expected: u8, actual: u8 },
    /// The last byte is not the stop flag (0xF2).
    MissingStopFlag { actual: u8 },
    /// The frame is too short to contain even a checksum (start + stop only).
    EmptyFrame,
    /// The frame is too short to contain the required header fields.
    FrameTooShort { minimum: usize, actual: usize },
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
            ParseError::MissingStartFlag { expected, actual } => {
                write!(
                    f,
                    "expected start flag 0x{expected:02X}, got 0x{actual:02X}"
                )
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
            ParseError::FrameTooShort { minimum, actual } => {
                write!(f, "frame too short: need {minimum} bytes, got {actual}")
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
        return Err(ParseError::MissingStartFlag {
            expected: STANDARD_START,
            actual: start,
        });
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

// ── Extended frame building ─────────────────────────────────────────────

/// Build an extended CSAFE frame from raw (unstuffed) `contents` with
/// destination and source addresses.
///
/// Returns the complete wire-format frame:
/// `[0xF0] [stuffed dst] [stuffed src] [stuffed contents] [stuffed checksum] [0xF2]`
///
/// Per the spec, addresses are byte-stuffed but **excluded from the
/// checksum** — the checksum covers only the frame contents.
///
/// # Errors
///
/// Returns [`FrameError::TooLarge`] if the resulting frame would exceed
/// the 120-byte protocol limit.
pub fn build_extended_frame(
    destination: u8,
    source: u8,
    contents: &[u8],
) -> Result<Vec<u8>, FrameError> {
    // Fast reject: if raw contents alone exceed the limit, the stuffed
    // frame (which is >= raw) certainly will too.
    if contents.len() > MAX_FRAME_SIZE {
        return Err(FrameError::TooLarge {
            actual: FRAME_ENVELOPE + contents.len() + 3, // rough lower bound
        });
    }

    let stuffed_dst = stuff_bytes(&[destination]);
    let stuffed_src = stuff_bytes(&[source]);
    let stuffed_contents = stuff_bytes(contents);
    let checksum = compute_checksum(contents);
    let stuffed_checksum = stuff_bytes(&[checksum]);

    let total = FRAME_ENVELOPE
        + stuffed_dst.len()
        + stuffed_src.len()
        + stuffed_contents.len()
        + stuffed_checksum.len();
    if total > MAX_FRAME_SIZE {
        return Err(FrameError::TooLarge { actual: total });
    }

    let mut frame = Vec::with_capacity(total);
    frame.push(EXTENDED_START);
    frame.extend_from_slice(&stuffed_dst);
    frame.extend_from_slice(&stuffed_src);
    frame.extend_from_slice(&stuffed_contents);
    frame.extend_from_slice(&stuffed_checksum);
    frame.push(STOP);
    Ok(frame)
}

// ── Extended frame parsing ──────────────────────────────────────────────

/// Parsed contents of an extended CSAFE frame.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExtendedFrame {
    /// Destination address (unstuffed).
    pub destination: u8,
    /// Source address (unstuffed).
    pub source: u8,
    /// Raw frame contents (unstuffed, checksum removed).
    pub contents: Vec<u8>,
}

/// Parse an extended CSAFE frame from wire bytes.
///
/// Expects the full frame including start/stop flags:
/// `[0xF0] [stuffed dst] [stuffed src] [stuffed contents + stuffed checksum] [0xF2]`
///
/// Steps:
/// 1. Validate start flag (0xF0) and stop flag (0xF2).
/// 2. Unstuff the body between the flags.
/// 3. Extract the first two bytes as destination and source addresses.
/// 4. Split the remaining body into contents and checksum.
/// 5. Validate checksum over **contents only** (addresses excluded).
///
/// # Errors
///
/// Returns [`ParseError`] for missing flags, frames too short for the
/// address header, unstuffing failures, or checksum mismatches.
pub fn parse_extended_frame(frame: &[u8]) -> Result<ExtendedFrame, ParseError> {
    if frame.is_empty() {
        return Err(ParseError::EmptyFrame);
    }

    if frame.len() > MAX_FRAME_SIZE {
        return Err(ParseError::TooLarge {
            actual: frame.len(),
        });
    }

    let start = frame[0];
    if start != EXTENDED_START {
        return Err(ParseError::MissingStartFlag {
            expected: EXTENDED_START,
            actual: start,
        });
    }

    let stop = *frame.last().unwrap();
    if stop != STOP {
        return Err(ParseError::MissingStopFlag { actual: stop });
    }

    let stuffed_body = &frame[1..frame.len() - 1];
    let unstuffed = unstuff_bytes(stuffed_body)?;

    // Need at least: dst(1) + src(1) + checksum(1) = 3 bytes.
    if unstuffed.len() < 3 {
        return Err(ParseError::FrameTooShort {
            minimum: 3,
            actual: unstuffed.len(),
        });
    }

    let destination = unstuffed[0];
    let source = unstuffed[1];

    // Everything after addresses: contents + checksum (last byte).
    let after_addrs = &unstuffed[2..];
    let (contents, checksum_slice) = after_addrs.split_at(after_addrs.len() - 1);
    let frame_checksum = checksum_slice[0];

    // Checksum covers contents only — addresses are excluded.
    let computed = compute_checksum(contents);
    if computed != frame_checksum {
        return Err(ParseError::BadChecksum {
            expected: frame_checksum,
            actual: computed,
        });
    }

    Ok(ExtendedFrame {
        destination,
        source,
        contents: contents.to_vec(),
    })
}

// ── Auto-detecting parser ───────────────────────────────────────────────

/// The result of parsing a frame whose type is not known in advance.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Frame {
    /// A standard frame containing raw contents.
    Standard(Vec<u8>),
    /// An extended frame with addressing and raw contents.
    Extended(ExtendedFrame),
}

/// Parse a CSAFE frame, auto-detecting standard vs extended by the start
/// flag byte.
///
/// - `0xF1` → standard frame → [`Frame::Standard`]
/// - `0xF0` → extended frame → [`Frame::Extended`]
/// - anything else → [`ParseError::MissingStartFlag`] (expected `0xF1`)
///
/// # Errors
///
/// Returns the same errors as the underlying parser for whichever frame
/// type is detected.
pub fn parse_frame(frame: &[u8]) -> Result<Frame, ParseError> {
    match frame.first() {
        Some(&STANDARD_START) => parse_standard_frame(frame).map(Frame::Standard),
        Some(&EXTENDED_START) => parse_extended_frame(frame).map(Frame::Extended),
        Some(&actual) => Err(ParseError::MissingStartFlag {
            expected: STANDARD_START,
            actual,
        }),
        None => Err(ParseError::EmptyFrame),
    }
}

// ── Unit tests ──────────────────────────────────────────────────────────

#[cfg(test)]
mod tests;
