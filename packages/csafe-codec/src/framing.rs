// CSAFE frame-level byte stuffing (protocol.yaml §byte_stuffing, Table 6).
//
// Byte stuffing ensures the four flag bytes 0xF0–0xF3 never appear inside
// frame contents or the checksum.  Each reserved byte is replaced by a
// two-byte escape sequence: [0xF3, byte − 0xF0].

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
    let mut out = Vec::with_capacity(data.len());
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
}
