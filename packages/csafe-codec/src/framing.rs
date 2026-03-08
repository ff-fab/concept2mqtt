// CSAFE frame-level primitives: byte stuffing, checksum, and frame building.
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
            actual: contents.len(),
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

// ── Unit tests ──────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // -- stuff_bytes ------------------------------------------------------

    #[test]
    fn stuff_empty() {
        let empty: Vec<u8> = vec![];
        assert_eq!(stuff_bytes(&[]), empty);
    }

    #[test]
    fn stuff_no_reserved_bytes() {
        let input = vec![0x00, 0x42, 0xEF, 0xFF];
        assert_eq!(stuff_bytes(&input), input);
    }

    #[test]
    fn stuff_each_reserved_byte() {
        // Table 6 — each reserved byte maps to [0xF3, offset].
        assert_eq!(stuff_bytes(&[0xF0]), vec![0xF3, 0x00]);
        assert_eq!(stuff_bytes(&[0xF1]), vec![0xF3, 0x01]);
        assert_eq!(stuff_bytes(&[0xF2]), vec![0xF3, 0x02]);
        assert_eq!(stuff_bytes(&[0xF3]), vec![0xF3, 0x03]);
    }

    #[test]
    fn stuff_mixed() {
        let input = vec![0x01, 0xF1, 0x02, 0xF3, 0x03];
        let expected = vec![0x01, 0xF3, 0x01, 0x02, 0xF3, 0x03, 0x03];
        assert_eq!(stuff_bytes(&input), expected);
    }

    #[test]
    fn stuff_all_reserved_consecutive() {
        let input = vec![0xF0, 0xF1, 0xF2, 0xF3];
        let expected = vec![0xF3, 0x00, 0xF3, 0x01, 0xF3, 0x02, 0xF3, 0x03];
        assert_eq!(stuff_bytes(&input), expected);
    }

    // -- unstuff_bytes ----------------------------------------------------

    #[test]
    fn unstuff_empty() {
        let empty: Vec<u8> = vec![];
        assert_eq!(unstuff_bytes(&[]).unwrap(), empty);
    }

    #[test]
    fn unstuff_no_escapes() {
        let input = vec![0x00, 0x42, 0xEF, 0xFF];
        assert_eq!(unstuff_bytes(&input).unwrap(), input);
    }

    #[test]
    fn unstuff_each_reserved_byte() {
        assert_eq!(unstuff_bytes(&[0xF3, 0x00]).unwrap(), vec![0xF0]);
        assert_eq!(unstuff_bytes(&[0xF3, 0x01]).unwrap(), vec![0xF1]);
        assert_eq!(unstuff_bytes(&[0xF3, 0x02]).unwrap(), vec![0xF2]);
        assert_eq!(unstuff_bytes(&[0xF3, 0x03]).unwrap(), vec![0xF3]);
    }

    #[test]
    fn unstuff_mixed() {
        let input = vec![0x01, 0xF3, 0x01, 0x02, 0xF3, 0x03, 0x03];
        let expected = vec![0x01, 0xF1, 0x02, 0xF3, 0x03];
        assert_eq!(unstuff_bytes(&input).unwrap(), expected);
    }

    // -- round-trip -------------------------------------------------------

    #[test]
    fn roundtrip_identity() {
        // stuff then unstuff should recover the original for any input.
        let original = vec![0x00, 0xF0, 0x7F, 0xF3, 0xF1, 0xF2, 0xFF];
        let stuffed = stuff_bytes(&original);
        let recovered = unstuff_bytes(&stuffed).unwrap();
        assert_eq!(recovered, original);
    }

    #[test]
    fn roundtrip_all_byte_values() {
        let original: Vec<u8> = (0x00..=0xFF).collect();
        let recovered = unstuff_bytes(&stuff_bytes(&original)).unwrap();
        assert_eq!(recovered, original);
    }

    // -- error cases ------------------------------------------------------

    #[test]
    fn unstuff_truncated_escape() {
        let err = unstuff_bytes(&[0x01, 0xF3]).unwrap_err();
        assert_eq!(err, StuffingError::TruncatedEscape { position: 1 });
    }

    #[test]
    fn unstuff_invalid_offset() {
        let err = unstuff_bytes(&[0xF3, 0x04]).unwrap_err();
        assert_eq!(
            err,
            StuffingError::InvalidOffset {
                position: 1,
                offset: 0x04
            }
        );
    }

    #[test]
    fn unstuff_invalid_offset_high() {
        let err = unstuff_bytes(&[0xF3, 0xFF]).unwrap_err();
        assert_eq!(
            err,
            StuffingError::InvalidOffset {
                position: 1,
                offset: 0xFF
            }
        );
    }

    // -- compute_checksum -------------------------------------------------

    #[test]
    fn checksum_empty() {
        assert_eq!(compute_checksum(&[]), 0x00);
    }

    #[test]
    fn checksum_single_byte() {
        assert_eq!(compute_checksum(&[0x42]), 0x42);
    }

    #[test]
    fn checksum_two_bytes() {
        // 0xAA ^ 0x55 = 0xFF
        assert_eq!(compute_checksum(&[0xAA, 0x55]), 0xFF);
    }

    #[test]
    fn checksum_self_cancelling() {
        // XOR of a byte with itself is 0.
        assert_eq!(compute_checksum(&[0x37, 0x37]), 0x00);
    }

    #[test]
    fn checksum_spec_crosscheck() {
        // pROWess cross-reference: XOR of frame contents [0x91] = 0x91.
        // A real CSAFE GETSERIAL command (short command 0x91, no data).
        assert_eq!(compute_checksum(&[0x91]), 0x91);
    }

    #[test]
    fn checksum_multi_byte_payload() {
        // Simulated payload: [0x01, 0x02, 0x03, 0x04]
        // 0x01 ^ 0x02 = 0x03; 0x03 ^ 0x03 = 0x00; 0x00 ^ 0x04 = 0x04
        assert_eq!(compute_checksum(&[0x01, 0x02, 0x03, 0x04]), 0x04);
    }

    #[test]
    fn checksum_all_ff() {
        // Three 0xFF bytes: 0xFF ^ 0xFF = 0x00; 0x00 ^ 0xFF = 0xFF
        assert_eq!(compute_checksum(&[0xFF, 0xFF, 0xFF]), 0xFF);
    }

    // -- validate_checksum ------------------------------------------------

    #[test]
    fn validate_correct() {
        let data = &[0x01, 0x02, 0x03, 0x04];
        assert!(validate_checksum(data, 0x04));
    }

    #[test]
    fn validate_incorrect() {
        let data = &[0x01, 0x02, 0x03, 0x04];
        assert!(!validate_checksum(data, 0x05));
    }

    #[test]
    fn validate_empty_with_zero() {
        assert!(validate_checksum(&[], 0x00));
    }

    #[test]
    fn validate_empty_with_nonzero() {
        assert!(!validate_checksum(&[], 0x01));
    }

    // -- checksum + stuffing integration ----------------------------------

    #[test]
    fn checksum_then_stuff_roundtrip() {
        // Simulate frame building: compute checksum, stuff the payload,
        // stuff the checksum byte, then unstuff and validate.
        let payload = vec![0x91]; // GETSERIAL short command
        let csum = compute_checksum(&payload);
        assert_eq!(csum, 0x91);

        let stuffed_payload = stuff_bytes(&payload);
        let stuffed_csum = stuff_bytes(&[csum]);

        let recovered_payload = unstuff_bytes(&stuffed_payload).unwrap();
        let recovered_csum_bytes = unstuff_bytes(&stuffed_csum).unwrap();

        assert!(validate_checksum(
            &recovered_payload,
            recovered_csum_bytes[0]
        ));
    }

    #[test]
    fn checksum_reserved_byte_roundtrip() {
        // Payload that produces a checksum in the reserved range.
        // 0xF1 ^ 0x00 = 0xF1 → checksum is 0xF1, needs stuffing.
        let payload = vec![0xF1];
        let csum = compute_checksum(&payload);
        assert_eq!(csum, 0xF1);

        // Checksum 0xF1 must be stuffed → [0xF3, 0x01]
        let stuffed_csum = stuff_bytes(&[csum]);
        assert_eq!(stuffed_csum, vec![0xF3, 0x01]);

        // Unstuff recovers the original checksum
        let recovered = unstuff_bytes(&stuffed_csum).unwrap();
        assert!(validate_checksum(&payload, recovered[0]));
    }

    // -- build_standard_frame ---------------------------------------------

    #[test]
    fn frame_empty_contents() {
        // Empty payload → checksum is 0x00 (no stuffing needed).
        // [0xF1, 0x00, 0xF2] = 3 bytes
        let frame = build_standard_frame(&[]).unwrap();
        assert_eq!(frame, vec![0xF1, 0x00, 0xF2]);
    }

    #[test]
    fn frame_single_command() {
        // GETSERIAL = 0x91.  Checksum = 0x91 (no stuffing needed).
        // [0xF1, 0x91, 0x91, 0xF2]
        let frame = build_standard_frame(&[0x91]).unwrap();
        assert_eq!(frame, vec![0xF1, 0x91, 0x91, 0xF2]);
    }

    #[test]
    fn frame_multi_byte_payload() {
        // Payload [0x01, 0x02] → checksum = 0x01 ^ 0x02 = 0x03.
        // No reserved bytes → no stuffing.
        // [0xF1, 0x01, 0x02, 0x03, 0xF2]
        let frame = build_standard_frame(&[0x01, 0x02]).unwrap();
        assert_eq!(frame, vec![0xF1, 0x01, 0x02, 0x03, 0xF2]);
    }

    #[test]
    fn frame_contents_need_stuffing() {
        // Payload [0xF1] → stuffed to [0xF3, 0x01].
        // Checksum = 0xF1 → stuffed to [0xF3, 0x01].
        // [0xF1, 0xF3, 0x01, 0xF3, 0x01, 0xF2] = 6 bytes
        let frame = build_standard_frame(&[0xF1]).unwrap();
        assert_eq!(frame, vec![0xF1, 0xF3, 0x01, 0xF3, 0x01, 0xF2]);
    }

    #[test]
    fn frame_checksum_needs_stuffing() {
        // Payload [0xF0] → stuffed to [0xF3, 0x00].
        // Checksum = 0xF0 → stuffed to [0xF3, 0x00].
        let frame = build_standard_frame(&[0xF0]).unwrap();
        assert_eq!(frame, vec![0xF1, 0xF3, 0x00, 0xF3, 0x00, 0xF2]);
    }

    #[test]
    fn frame_all_reserved_bytes() {
        // Payload [0xF0, 0xF1, 0xF2, 0xF3].
        // Stuffed contents: [0xF3,0x00, 0xF3,0x01, 0xF3,0x02, 0xF3,0x03] = 8 bytes.
        // Checksum = 0xF0 ^ 0xF1 ^ 0xF2 ^ 0xF3 = 0x00 (no stuffing).
        // Total: [0xF1, ..8 stuffed.., 0x00, 0xF2] = 11 bytes.
        let frame = build_standard_frame(&[0xF0, 0xF1, 0xF2, 0xF3]).unwrap();
        assert_eq!(
            frame,
            vec![0xF1, 0xF3, 0x00, 0xF3, 0x01, 0xF3, 0x02, 0xF3, 0x03, 0x00, 0xF2]
        );
    }

    #[test]
    fn frame_starts_with_start_flag() {
        let frame = build_standard_frame(&[0x42]).unwrap();
        assert_eq!(frame[0], STANDARD_START);
    }

    #[test]
    fn frame_ends_with_stop_flag() {
        let frame = build_standard_frame(&[0x42]).unwrap();
        assert_eq!(*frame.last().unwrap(), STOP);
    }

    #[test]
    fn frame_checksum_is_valid() {
        // Build a frame and verify the checksum embeds correctly.
        let contents = &[0x01, 0x02, 0x03, 0x04]; // checksum = 0x04
        let frame = build_standard_frame(contents).unwrap();
        // Frame: [0xF1, 0x01, 0x02, 0x03, 0x04, 0x04, 0xF2]
        // Extract: stuffed body [1..len-2], stuffed checksum [len-2..len-1]
        // In this case no stuffing occurred, so body = frame[1..5], csum = frame[5].
        let recovered_contents = &frame[1..frame.len() - 2];
        let recovered_csum = frame[frame.len() - 2];
        assert!(validate_checksum(recovered_contents, recovered_csum));
    }

    #[test]
    fn frame_no_flags_in_body() {
        // A frame with reserved bytes in payload should have no raw
        // flag bytes between start and stop.
        let frame = build_standard_frame(&[0xF0, 0xF1, 0xF2, 0xF3]).unwrap();
        let body = &frame[1..frame.len() - 1]; // between start and stop
        for &b in body {
            assert!(
                !STUFF_RANGE.contains(&b) || b == STUFF_MARKER,
                "unexpected raw flag byte 0x{b:02X} in frame body"
            );
        }
    }

    #[test]
    fn frame_too_large() {
        // 120 bytes max.  Start(1) + stop(1) = 2 overhead.
        // In the worst case every content byte is stuffed (2× expansion)
        // plus the checksum may be stuffed (2 bytes).
        // With 59 bytes of non-reserved content: stuffed = 59 bytes,
        // checksum is 1 byte → total = 1 + 59 + 1 + 1 = 62.  Fine.
        // Fill with 118 non-reserved bytes: stuffed = 118, checksum 1–2,
        // total = 1 + 118 + 1 + 1 = 121 → too large.
        let payload = vec![0x01; 118];
        let result = build_standard_frame(&payload);
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), FrameError::TooLarge { actual: 121 });
    }

    #[test]
    fn frame_exactly_at_limit() {
        // 117 non-reserved content bytes.
        // Checksum = XOR of 117 copies of 0x01 = 0x01 (odd count).
        // Stuffed contents = 117, stuffed checksum = 1.
        // Total = 1 + 117 + 1 + 1 = 120 → exactly at limit.
        let payload = vec![0x01; 117];
        let frame = build_standard_frame(&payload).unwrap();
        assert_eq!(frame.len(), 120);
    }

    #[test]
    fn frame_reserved_payload_expansion() {
        // All-0xF0 payload: each byte doubles.
        // 55 bytes → stuffed to 110.  Checksum 0xF0 (odd count) → stuffed to 2.
        // Total = 1 + 110 + 2 + 1 = 114 → fits.
        let payload = vec![0xF0; 55];
        let frame = build_standard_frame(&payload).unwrap();
        assert_eq!(frame.len(), 114);

        // 58 bytes → stuffed to 116.  Checksum 0x00 (even count) → 1 byte.
        // Total = 1 + 116 + 1 + 1 = 119 → fits.
        let payload = vec![0xF0; 58];
        let frame = build_standard_frame(&payload).unwrap();
        assert_eq!(frame.len(), 119);

        // 59 bytes → stuffed to 118.  Checksum 0xF0 (odd count) → 2 bytes.
        // Total = 1 + 118 + 2 + 1 = 122 → too large.
        let payload = vec![0xF0; 59];
        assert!(build_standard_frame(&payload).is_err());
    }

    #[test]
    fn frame_error_display() {
        let err = FrameError::TooLarge { actual: 130 };
        assert_eq!(
            err.to_string(),
            "frame size 130 bytes exceeds 120-byte limit"
        );
    }

    #[test]
    fn frame_huge_input_fast_reject() {
        // Inputs larger than MAX_FRAME_SIZE are rejected immediately
        // without allocating a stuffed buffer.
        let payload = vec![0x01; 1024];
        let result = build_standard_frame(&payload);
        assert!(result.is_err());
    }
}
