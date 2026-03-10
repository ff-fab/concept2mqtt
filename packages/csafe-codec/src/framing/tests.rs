use super::*;
use smallvec::smallvec;

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

// -- stuff_into -------------------------------------------------------

#[test]
fn stuff_into_appends_to_existing_buffer() {
    let mut buf = StuffBuf::new();
    buf.push(0xAA); // pre-existing byte
    stuff_into(&[0x01, 0xF1], &mut buf);
    assert_eq!(&buf[..], &[0xAA, 0x01, 0xF3, 0x01]);
}

#[test]
fn stuff_into_empty_input() {
    let mut buf = StuffBuf::new();
    stuff_into(&[], &mut buf);
    assert!(buf.is_empty());
}

#[test]
fn stuff_into_all_reserved() {
    let mut buf = StuffBuf::new();
    stuff_into(&[0xF0, 0xF1, 0xF2, 0xF3], &mut buf);
    assert_eq!(&buf[..], &[0xF3, 0x00, 0xF3, 0x01, 0xF3, 0x02, 0xF3, 0x03]);
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

// -- unstuff_into -----------------------------------------------------

#[test]
fn unstuff_into_appends_to_existing_buffer() {
    let mut buf = FrameBuf::new();
    buf.push(0xBB); // pre-existing byte
    unstuff_into(&[0xF3, 0x01, 0x42], &mut buf).unwrap();
    assert_eq!(&buf[..], &[0xBB, 0xF1, 0x42]);
}

#[test]
fn unstuff_into_empty_input() {
    let mut buf = FrameBuf::new();
    unstuff_into(&[], &mut buf).unwrap();
    assert!(buf.is_empty());
}

#[test]
fn unstuff_into_error_preserves_preexisting_data() {
    let mut buf = FrameBuf::new();
    buf.push(0xCC);
    let result = unstuff_into(&[0x01, 0xF3], &mut buf); // truncated escape
    assert!(result.is_err());
    // Buffer may contain partial output up to the error — that's fine,
    // callers should discard on error. But the pre-existing byte is intact.
    assert_eq!(buf[0], 0xCC);
}

#[test]
fn unstuff_into_all_escapes() {
    let mut buf = FrameBuf::new();
    unstuff_into(&[0xF3, 0x00, 0xF3, 0x01, 0xF3, 0x02, 0xF3, 0x03], &mut buf).unwrap();
    assert_eq!(&buf[..], &[0xF0, 0xF1, 0xF2, 0xF3]);
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
    assert_eq!(
        result.unwrap_err(),
        FrameError::TooLarge {
            actual: FRAME_ENVELOPE + 1024 + 1
        }
    );
}

// -- build_standard_frame_into ----------------------------------------

#[test]
fn frame_into_appends_to_existing_buffer() {
    let mut buf = FrameBuf::new();
    buf.push(0xFF); // pre-existing byte
    build_standard_frame_into(&[0x91], &mut buf).unwrap();
    // 0xFF + [0xF1, 0x91, 0x91, 0xF2]
    assert_eq!(&buf[..], &[0xFF, 0xF1, 0x91, 0x91, 0xF2]);
}

#[test]
fn frame_into_empty_contents() {
    let mut buf = FrameBuf::new();
    build_standard_frame_into(&[], &mut buf).unwrap();
    assert_eq!(&buf[..], &[0xF1, 0x00, 0xF2]);
}

#[test]
fn frame_into_too_large_leaves_buffer_unchanged() {
    let mut buf = FrameBuf::new();
    buf.push(0xAA);
    let payload = vec![0x01; 118];
    let result = build_standard_frame_into(&payload, &mut buf);
    assert!(result.is_err());
    assert_eq!(&buf[..], &[0xAA]); // buffer unchanged
}

#[test]
fn frame_into_stuffed_contents() {
    let mut buf = FrameBuf::new();
    build_standard_frame_into(&[0xF1], &mut buf).unwrap();
    assert_eq!(&buf[..], &[0xF1, 0xF3, 0x01, 0xF3, 0x01, 0xF2]);
}

// -- parse_standard_frame ---------------------------------------------

#[test]
fn parse_empty_input() {
    assert_eq!(parse_standard_frame(&[]), Err(ParseError::EmptyFrame));
}

#[test]
fn parse_missing_start_flag() {
    // Starts with 0x00 instead of 0xF1.
    assert_eq!(
        parse_standard_frame(&[0x00, 0x42, 0x42, 0xF2]),
        Err(ParseError::MissingStartFlag {
            expected: STANDARD_START,
            actual: 0x00,
        })
    );
}

#[test]
fn parse_extended_start_rejected() {
    // Extended start flag 0xF0 is not a standard frame.
    assert_eq!(
        parse_standard_frame(&[0xF0, 0x42, 0x42, 0xF2]),
        Err(ParseError::MissingStartFlag {
            expected: STANDARD_START,
            actual: 0xF0,
        })
    );
}

#[test]
fn parse_missing_stop_flag() {
    // Ends with 0xFF instead of 0xF2.
    assert_eq!(
        parse_standard_frame(&[0xF1, 0x42, 0x42, 0xFF]),
        Err(ParseError::MissingStopFlag { actual: 0xFF })
    );
}

#[test]
fn parse_only_flags_no_checksum() {
    // [0xF1, 0xF2] — start and stop but no body at all.
    assert_eq!(
        parse_standard_frame(&[0xF1, 0xF2]),
        Err(ParseError::EmptyFrame)
    );
}

#[test]
fn parse_empty_contents_with_checksum() {
    // Empty contents → checksum = 0x00.
    // Wire: [0xF1, 0x00, 0xF2]
    let contents = parse_standard_frame(&[0xF1, 0x00, 0xF2]).unwrap();
    assert!(contents.is_empty());
}

#[test]
fn parse_single_command() {
    // GETSERIAL 0x91.  Checksum = 0x91.
    // Wire: [0xF1, 0x91, 0x91, 0xF2]
    let contents = parse_standard_frame(&[0xF1, 0x91, 0x91, 0xF2]).unwrap();
    assert_eq!(&contents[..], &[0x91]);
}

#[test]
fn parse_multi_byte_payload() {
    // Payload [0x01, 0x02], checksum = 0x03.
    let contents = parse_standard_frame(&[0xF1, 0x01, 0x02, 0x03, 0xF2]).unwrap();
    assert_eq!(&contents[..], &[0x01, 0x02]);
}

#[test]
fn parse_stuffed_contents() {
    // Payload [0xF1] → stuffed to [0xF3, 0x01].
    // Checksum = 0xF1 → stuffed to [0xF3, 0x01].
    // Wire: [0xF1, 0xF3, 0x01, 0xF3, 0x01, 0xF2]
    let contents = parse_standard_frame(&[0xF1, 0xF3, 0x01, 0xF3, 0x01, 0xF2]).unwrap();
    assert_eq!(&contents[..], &[0xF1]);
}

#[test]
fn parse_bad_checksum() {
    // Payload [0x01], correct checksum would be 0x01, but we say 0xFF.
    let result = parse_standard_frame(&[0xF1, 0x01, 0xFF, 0xF2]);
    assert_eq!(
        result,
        Err(ParseError::BadChecksum {
            expected: 0xFF,
            actual: 0x01
        })
    );
}

#[test]
fn parse_truncated_escape() {
    // Wire: [0xF1, 0xF3, 0xF2] — 0xF3 followed immediately by stop flag.
    // unstuff_bytes sees [0xF3] (just one byte) → TruncatedEscape.
    let result = parse_standard_frame(&[0xF1, 0xF3, 0xF2]);
    assert!(matches!(
        result,
        Err(ParseError::Unstuffing(
            StuffingError::TruncatedEscape { .. }
        ))
    ));
}

#[test]
fn parse_invalid_escape_offset() {
    // Wire: [0xF1, 0xF3, 0x10, 0xF2] — offset 0x10 is invalid.
    let result = parse_standard_frame(&[0xF1, 0xF3, 0x10, 0xF2]);
    assert!(matches!(
        result,
        Err(ParseError::Unstuffing(StuffingError::InvalidOffset { .. }))
    ));
}

#[test]
fn parse_too_large() {
    // A frame exceeding MAX_FRAME_SIZE should be rejected immediately.
    let mut frame = vec![0x00; MAX_FRAME_SIZE + 1];
    frame[0] = STANDARD_START;
    *frame.last_mut().unwrap() = STOP;
    let result = parse_standard_frame(&frame);
    assert_eq!(
        result,
        Err(ParseError::TooLarge {
            actual: MAX_FRAME_SIZE + 1
        })
    );
}

// -- build + parse roundtrip ------------------------------------------

#[test]
fn roundtrip_build_then_parse() {
    let original = vec![0x91]; // GETSERIAL
    let frame = build_standard_frame(&original).unwrap();
    let recovered = parse_standard_frame(&frame).unwrap();
    assert_eq!(&recovered[..], &original[..]);
}

#[test]
fn roundtrip_with_reserved_bytes() {
    let original = vec![0xF0, 0xF1, 0xF2, 0xF3, 0x42];
    let frame = build_standard_frame(&original).unwrap();
    let recovered = parse_standard_frame(&frame).unwrap();
    assert_eq!(&recovered[..], &original[..]);
}

#[test]
fn roundtrip_multi_byte() {
    let original = vec![0x01, 0x02, 0x03, 0x04, 0x05];
    let frame = build_standard_frame(&original).unwrap();
    let recovered = parse_standard_frame(&frame).unwrap();
    assert_eq!(&recovered[..], &original[..]);
}

#[test]
fn roundtrip_empty_contents() {
    let original: Vec<u8> = vec![];
    let frame = build_standard_frame(&original).unwrap();
    let recovered = parse_standard_frame(&frame).unwrap();
    assert_eq!(&recovered[..], &original[..]);
}

#[test]
fn roundtrip_all_single_bytes_via_frame() {
    // Build and parse a frame for every possible single-byte payload.
    for b in 0x00..=0xFFu8 {
        let original = vec![b];
        let frame = build_standard_frame(&original).unwrap();
        let recovered = parse_standard_frame(&frame).unwrap();
        assert_eq!(
            &recovered[..],
            &original[..],
            "roundtrip failed for byte 0x{b:02X}"
        );
    }
}

// -- parse error display ----------------------------------------------

#[test]
fn parse_error_display_missing_start() {
    let err = ParseError::MissingStartFlag {
        expected: STANDARD_START,
        actual: 0x00,
    };
    assert_eq!(err.to_string(), "expected start flag 0xF1, got 0x00");
}

#[test]
fn parse_error_display_bad_checksum() {
    let err = ParseError::BadChecksum {
        expected: 0xAA,
        actual: 0xBB,
    };
    assert_eq!(
        err.to_string(),
        "checksum mismatch: frame has 0xAA, computed 0xBB"
    );
}

#[test]
fn parse_error_display_too_large() {
    let err = ParseError::TooLarge { actual: 200 };
    assert_eq!(
        err.to_string(),
        "frame size 200 bytes exceeds 120-byte limit"
    );
}

#[test]
fn parse_error_from_stuffing_error() {
    // Verify From<StuffingError> conversion works.
    let stuffing_err = StuffingError::TruncatedEscape { position: 5 };
    let parse_err: ParseError = stuffing_err.clone().into();
    assert_eq!(parse_err, ParseError::Unstuffing(stuffing_err));
}

// -- extended frame: build_extended_frame -----------------------------

#[test]
fn ext_build_simple() {
    // dst=0xFD, src=0x00, contents=[0x91]
    // checksum = 0x91 (XOR of contents only, addresses excluded)
    let frame = build_extended_frame(0xFD, 0x00, &[0x91]).unwrap();
    assert_eq!(frame, vec![0xF0, 0xFD, 0x00, 0x91, 0x91, 0xF2]);
}

#[test]
fn ext_build_starts_with_extended_flag() {
    let frame = build_extended_frame(0x00, 0x00, &[0x42]).unwrap();
    assert_eq!(frame[0], EXTENDED_START);
}

#[test]
fn ext_build_ends_with_stop_flag() {
    let frame = build_extended_frame(0x00, 0x00, &[0x42]).unwrap();
    assert_eq!(*frame.last().unwrap(), STOP);
}

#[test]
fn ext_build_empty_contents() {
    // Contents empty → checksum = 0x00.
    let frame = build_extended_frame(0xFD, 0x00, &[]).unwrap();
    assert_eq!(frame, vec![0xF0, 0xFD, 0x00, 0x00, 0xF2]);
}

#[test]
fn ext_build_address_stuffing() {
    // src=0xF1 needs stuffing → [0xF3, 0x01].
    let frame = build_extended_frame(0x00, 0xF1, &[0x91]).unwrap();
    // [0xF0] [0x00] [0xF3, 0x01] [0x91] [0x91] [0xF2]
    assert_eq!(frame, vec![0xF0, 0x00, 0xF3, 0x01, 0x91, 0x91, 0xF2]);
}

#[test]
fn ext_build_both_addresses_stuffed() {
    // dst=0xF0, src=0xF3 both need stuffing.
    let frame = build_extended_frame(0xF0, 0xF3, &[0x42]).unwrap();
    // dst: 0xF0 → [0xF3, 0x00], src: 0xF3 → [0xF3, 0x03]
    // contents: [0x42], checksum: 0x42
    assert_eq!(frame, vec![0xF0, 0xF3, 0x00, 0xF3, 0x03, 0x42, 0x42, 0xF2]);
}

#[test]
fn ext_build_contents_stuffed() {
    // contents=[0xF0] → stuffed=[0xF3, 0x00], checksum=0xF0 → [0xF3, 0x00]
    let frame = build_extended_frame(0x00, 0x00, &[0xF0]).unwrap();
    assert_eq!(frame, vec![0xF0, 0x00, 0x00, 0xF3, 0x00, 0xF3, 0x00, 0xF2]);
}

#[test]
fn ext_build_checksum_excludes_addresses() {
    // Verify the checksum is computed over contents only.
    // contents=[0x01, 0x02, 0x03], checksum = 0x01^0x02^0x03 = 0x00
    let frame = build_extended_frame(0xFF, 0xFD, &[0x01, 0x02, 0x03]).unwrap();
    // Unstuff body to verify checksum.
    let body = &frame[1..frame.len() - 1];
    let unstuffed = unstuff_bytes(body).unwrap();
    // unstuffed: [0xFF, 0xFD, 0x01, 0x02, 0x03, 0x00]
    let csum = unstuffed.last().unwrap();
    assert_eq!(*csum, 0x00); // XOR of contents only
}

#[test]
fn ext_build_too_large() {
    // Contents so large the frame would exceed 120 bytes.
    let result = build_extended_frame(0x00, 0x00, &[0x01; 116]);
    assert!(result.is_err());
    if let Err(FrameError::TooLarge { actual }) = result {
        assert!(actual > MAX_FRAME_SIZE);
    }
}

#[test]
fn ext_build_fast_reject() {
    // Raw contents > MAX_FRAME_SIZE triggers fast-reject path.
    let result = build_extended_frame(0x00, 0x00, &[0x01; 121]);
    assert!(matches!(result, Err(FrameError::TooLarge { .. })));
}

// -- build_extended_frame_into ----------------------------------------

#[test]
fn ext_frame_into_appends_to_existing_buffer() {
    let mut buf = FrameBuf::new();
    buf.push(0xFF);
    build_extended_frame_into(0x00, 0x01, &[0x42], &mut buf).unwrap();
    // 0xFF + [0xF0, 0x00, 0x01, 0x42, 0x42, 0xF2]
    assert_eq!(&buf[..], &[0xFF, 0xF0, 0x00, 0x01, 0x42, 0x42, 0xF2]);
}

#[test]
fn ext_frame_into_too_large_leaves_buffer_unchanged() {
    let mut buf = FrameBuf::new();
    buf.push(0xBB);
    let payload = vec![0x01; 118];
    let result = build_extended_frame_into(0x00, 0x01, &payload, &mut buf);
    assert!(result.is_err());
    assert_eq!(&buf[..], &[0xBB]);
}

#[test]
fn ext_frame_into_addresses_need_stuffing() {
    let mut buf = FrameBuf::new();
    build_extended_frame_into(0xF0, 0xF1, &[0x42], &mut buf).unwrap();
    // Addresses stuffed: dst=0xF0→[0xF3,0x00], src=0xF1→[0xF3,0x01]
    // Contents: 0x42 (no stuffing), checksum=0x42 (no stuffing)
    assert_eq!(&buf[..], &[0xF0, 0xF3, 0x00, 0xF3, 0x01, 0x42, 0x42, 0xF2]);
}

// -- extended frame: parse_extended_frame -----------------------------

#[test]
fn ext_parse_simple() {
    let frame = vec![0xF0, 0xFD, 0x00, 0x91, 0x91, 0xF2];
    let parsed = parse_extended_frame(&frame).unwrap();
    assert_eq!(parsed.destination, 0xFD);
    assert_eq!(parsed.source, 0x00);
    assert_eq!(&parsed.contents[..], &[0x91]);
}

#[test]
fn ext_parse_empty_contents() {
    let frame = vec![0xF0, 0xFD, 0x00, 0x00, 0xF2];
    let parsed = parse_extended_frame(&frame).unwrap();
    assert_eq!(parsed.destination, 0xFD);
    assert_eq!(parsed.source, 0x00);
    assert!(parsed.contents.is_empty());
}

#[test]
fn ext_parse_stuffed_addresses() {
    // src=0xF1 → wire: [0xF3, 0x01]
    let frame = vec![0xF0, 0x00, 0xF3, 0x01, 0x91, 0x91, 0xF2];
    let parsed = parse_extended_frame(&frame).unwrap();
    assert_eq!(parsed.source, 0xF1);
    assert_eq!(&parsed.contents[..], &[0x91]);
}

#[test]
fn ext_parse_stuffed_contents() {
    // contents=[0xF0], checksum=0xF0 — both stuffed on wire.
    let frame = vec![0xF0, 0x00, 0x00, 0xF3, 0x00, 0xF3, 0x00, 0xF2];
    let parsed = parse_extended_frame(&frame).unwrap();
    assert_eq!(&parsed.contents[..], &[0xF0]);
}

#[test]
fn ext_parse_empty_input() {
    assert_eq!(parse_extended_frame(&[]), Err(ParseError::EmptyFrame));
}

#[test]
fn ext_parse_wrong_start_flag() {
    // Standard start flag 0xF1 is not an extended frame.
    assert_eq!(
        parse_extended_frame(&[0xF1, 0x00, 0x00, 0x00, 0xF2]),
        Err(ParseError::MissingStartFlag {
            expected: EXTENDED_START,
            actual: 0xF1,
        })
    );
}

#[test]
fn ext_parse_missing_stop_flag() {
    assert_eq!(
        parse_extended_frame(&[0xF0, 0x00, 0x00, 0x00, 0xFF]),
        Err(ParseError::MissingStopFlag { actual: 0xFF })
    );
}

#[test]
fn ext_parse_too_short_for_addresses() {
    // Body has only 2 unstuffed bytes: dst + src, no room for checksum.
    let frame = vec![0xF0, 0x00, 0x00, 0xF2];
    assert_eq!(
        parse_extended_frame(&frame),
        Err(ParseError::FrameTooShort {
            minimum: 3,
            actual: 2,
        })
    );
}

#[test]
fn ext_parse_too_short_body_one_byte() {
    // Body has only 1 unstuffed byte (just dst).
    let frame = vec![0xF0, 0x00, 0xF2];
    assert_eq!(
        parse_extended_frame(&frame),
        Err(ParseError::FrameTooShort {
            minimum: 3,
            actual: 1,
        })
    );
}

#[test]
fn ext_parse_bad_checksum() {
    // dst=0x00, src=0x00, contents=[0x01], bad checksum=0xFF
    let frame = vec![0xF0, 0x00, 0x00, 0x01, 0xFF, 0xF2];
    assert_eq!(
        parse_extended_frame(&frame),
        Err(ParseError::BadChecksum {
            expected: 0xFF,
            actual: 0x01,
        })
    );
}

#[test]
fn ext_parse_too_large() {
    let mut frame = vec![0u8; 121];
    frame[0] = EXTENDED_START;
    *frame.last_mut().unwrap() = STOP;
    assert_eq!(
        parse_extended_frame(&frame),
        Err(ParseError::TooLarge { actual: 121 })
    );
}

// -- extended frame round-trip ----------------------------------------

#[test]
fn ext_roundtrip_simple() {
    let ef = build_extended_frame(0xFD, 0x00, &[0x91]).unwrap();
    let parsed = parse_extended_frame(&ef).unwrap();
    assert_eq!(parsed.destination, 0xFD);
    assert_eq!(parsed.source, 0x00);
    assert_eq!(&parsed.contents[..], &[0x91]);
}

#[test]
fn ext_roundtrip_reserved_bytes_in_contents() {
    let original = vec![0xF0, 0xF1, 0xF2, 0xF3, 0x42];
    let frame = build_extended_frame(0xFD, 0x00, &original).unwrap();
    let parsed = parse_extended_frame(&frame).unwrap();
    assert_eq!(&parsed.contents[..], &original[..]);
}

#[test]
fn ext_roundtrip_reserved_addresses() {
    // Both addresses are reserved bytes needing stuffing.
    let frame = build_extended_frame(0xF0, 0xF3, &[0x42]).unwrap();
    let parsed = parse_extended_frame(&frame).unwrap();
    assert_eq!(parsed.destination, 0xF0);
    assert_eq!(parsed.source, 0xF3);
    assert_eq!(&parsed.contents[..], &[0x42]);
}

#[test]
fn ext_roundtrip_empty_contents() {
    let frame = build_extended_frame(0x00, 0x00, &[]).unwrap();
    let parsed = parse_extended_frame(&frame).unwrap();
    assert_eq!(parsed.destination, 0x00);
    assert_eq!(parsed.source, 0x00);
    assert!(parsed.contents.is_empty());
}

#[test]
fn ext_roundtrip_all_single_bytes() {
    // Every possible single-byte payload survives the extended round-trip.
    for b in 0x00..=0xFFu8 {
        let original = vec![b];
        let frame = build_extended_frame(ADDR_DEFAULT_SECONDARY, ADDR_PC_HOST, &original).unwrap();
        let parsed = parse_extended_frame(&frame).unwrap();
        assert_eq!(
            &parsed.contents[..],
            &original[..],
            "round-trip failed for byte 0x{b:02X}"
        );
    }
}

// -- parse_frame (auto-detect) ----------------------------------------

#[test]
fn parse_frame_standard() {
    let wire = build_standard_frame(&[0x91]).unwrap();
    let result = parse_frame(&wire).unwrap();
    assert_eq!(result, Frame::Standard(smallvec![0x91]));
}

#[test]
fn parse_frame_extended() {
    let wire = build_extended_frame(0xFD, 0x00, &[0x91]).unwrap();
    let result = parse_frame(&wire).unwrap();
    assert_eq!(
        result,
        Frame::Extended(ExtendedFrame {
            destination: 0xFD,
            source: 0x00,
            contents: smallvec![0x91],
        })
    );
}

#[test]
fn parse_frame_empty() {
    assert_eq!(parse_frame(&[]), Err(ParseError::EmptyFrame));
}

#[test]
fn parse_frame_unknown_start() {
    assert_eq!(
        parse_frame(&[0x00, 0x42, 0xF2]),
        Err(ParseError::MissingStartFlag {
            expected: STANDARD_START,
            actual: 0x00,
        })
    );
}

// -- extended frame error display -------------------------------------

#[test]
fn ext_parse_error_display_missing_start() {
    let err = ParseError::MissingStartFlag {
        expected: EXTENDED_START,
        actual: 0xF1,
    };
    assert_eq!(err.to_string(), "expected start flag 0xF0, got 0xF1");
}

#[test]
fn ext_parse_error_display_frame_too_short() {
    let err = ParseError::FrameTooShort {
        minimum: 3,
        actual: 1,
    };
    assert_eq!(err.to_string(), "frame too short: need 3 bytes, got 1");
}
