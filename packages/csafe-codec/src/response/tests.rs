use super::*;

// ── StatusByte parsing ─────────────────────────────────────────────────

#[test]
fn parse_status_byte_idle_ok_no_toggle() {
    // bit 7=0, bits 5-4=00 (Ok), bits 3-0=0x02 (Idle)
    let status = parse_status_byte(0x02).unwrap();
    assert!(!status.frame_toggle);
    assert_eq!(status.prev_frame_status, PrevFrameStatus::Ok);
    assert_eq!(status.server_state, ServerState::Idle);
}

#[test]
fn parse_status_byte_ready_ok_with_toggle() {
    // bit 7=1, bits 5-4=00 (Ok), bits 3-0=0x01 (Ready)
    let status = parse_status_byte(0x81).unwrap();
    assert!(status.frame_toggle);
    assert_eq!(status.prev_frame_status, PrevFrameStatus::Ok);
    assert_eq!(status.server_state, ServerState::Ready);
}

#[test]
fn parse_status_byte_in_use_reject() {
    // bit 7=0, bits 5-4=01 (Reject), bits 3-0=0x05 (InUse)
    let status = parse_status_byte(0x15).unwrap();
    assert!(!status.frame_toggle);
    assert_eq!(status.prev_frame_status, PrevFrameStatus::Reject);
    assert_eq!(status.server_state, ServerState::InUse);
}

#[test]
fn parse_status_byte_finish_bad() {
    // bit 7=0, bits 5-4=10 (Bad), bits 3-0=0x07 (Finish)
    let status = parse_status_byte(0x27).unwrap();
    assert!(!status.frame_toggle);
    assert_eq!(status.prev_frame_status, PrevFrameStatus::Bad);
    assert_eq!(status.server_state, ServerState::Finish);
}

#[test]
fn parse_status_byte_error_not_ready_with_toggle() {
    // bit 7=1, bits 5-4=11 (NotReady), bits 3-0=0x00 (Error)
    let status = parse_status_byte(0xB0).unwrap();
    assert!(status.frame_toggle);
    assert_eq!(status.prev_frame_status, PrevFrameStatus::NotReady);
    assert_eq!(status.server_state, ServerState::Error);
}

#[test]
fn parse_status_byte_all_server_states() {
    let cases: &[(u8, ServerState)] = &[
        (0x00, ServerState::Error),
        (0x01, ServerState::Ready),
        (0x02, ServerState::Idle),
        (0x03, ServerState::HaveId),
        (0x05, ServerState::InUse),
        (0x06, ServerState::Pause),
        (0x07, ServerState::Finish),
        (0x08, ServerState::Manual),
        (0x09, ServerState::Offline),
    ];
    for &(raw, expected_state) in cases {
        let status = parse_status_byte(raw).unwrap();
        assert_eq!(status.server_state, expected_state, "raw = 0x{raw:02X}");
    }
}

#[test]
fn parse_status_byte_invalid_server_state() {
    // 0x04 is not defined
    assert_eq!(
        parse_status_byte(0x04),
        Err(ResponseError::InvalidServerState { value: 0x04 })
    );
    // 0x0A–0x0F are not defined
    assert_eq!(
        parse_status_byte(0x0A),
        Err(ResponseError::InvalidServerState { value: 0x0A })
    );
    assert_eq!(
        parse_status_byte(0x0F),
        Err(ResponseError::InvalidServerState { value: 0x0F })
    );
}

#[test]
fn parse_status_byte_reserved_bit6_ignored() {
    // bit 6 is reserved — set it and verify it doesn't affect parsing.
    // 0x42 = bit 6 set, bits 5-4=00 (Ok), bits 3-0=0x02 (Idle)
    let status = parse_status_byte(0x42).unwrap();
    assert!(!status.frame_toggle);
    assert_eq!(status.prev_frame_status, PrevFrameStatus::Ok);
    assert_eq!(status.server_state, ServerState::Idle);
}

// ── ServerState TryFrom ─────────────────────────────────────────────────

#[test]
fn server_state_display() {
    assert_eq!(ServerState::Ready.to_string(), "Ready");
    assert_eq!(ServerState::InUse.to_string(), "InUse");
    assert_eq!(ServerState::Offline.to_string(), "Offline");
}

#[test]
fn prev_frame_status_display() {
    assert_eq!(PrevFrameStatus::Ok.to_string(), "Ok");
    assert_eq!(PrevFrameStatus::Reject.to_string(), "Reject");
    assert_eq!(PrevFrameStatus::Bad.to_string(), "Bad");
    assert_eq!(PrevFrameStatus::NotReady.to_string(), "NotReady");
}

// ── parse_response: empty/status-only ───────────────────────────────────

#[test]
fn parse_response_empty_returns_error() {
    assert_eq!(parse_response(&[]), Err(ResponseError::Empty));
}

#[test]
fn parse_response_status_only() {
    // PM in Idle, previous frame Ok, no toggle — no command responses.
    let resp = parse_response(&[0x02]).unwrap();
    assert_eq!(resp.status.server_state, ServerState::Idle);
    assert_eq!(resp.status.prev_frame_status, PrevFrameStatus::Ok);
    assert!(!resp.status.frame_toggle);
    assert!(resp.commands.is_empty());
}

// ── parse_response: single command response ─────────────────────────────

#[test]
fn parse_response_single_short_command() {
    // Response to GetStatus: status byte + [0x80, 0x01, <status>]
    let contents = &[0x01, 0x80, 0x01, 0x01];
    let resp = parse_response(contents).unwrap();
    assert_eq!(resp.status.server_state, ServerState::Ready);
    assert_eq!(resp.commands.len(), 1);
    assert_eq!(resp.commands[0].command_id, 0x80);
    assert_eq!(resp.commands[0].data, vec![0x01]);
}

#[test]
fn parse_response_command_with_no_data() {
    // Some commands echo back with byte_count=0
    let contents = &[0x02, 0x82, 0x00];
    let resp = parse_response(contents).unwrap();
    assert_eq!(resp.status.server_state, ServerState::Idle);
    assert_eq!(resp.commands.len(), 1);
    assert_eq!(resp.commands[0].command_id, 0x82);
    assert!(resp.commands[0].data.is_empty());
}

#[test]
fn parse_response_command_with_multi_byte_data() {
    // GetVersion response: [0x91, 0x05, mfg_id, cid, model, fw_ver_hi, fw_ver_lo]
    let contents = &[0x01, 0x91, 0x05, 22, 2, 5, 168, 50];
    let resp = parse_response(contents).unwrap();
    assert_eq!(resp.commands.len(), 1);
    assert_eq!(resp.commands[0].command_id, 0x91);
    assert_eq!(resp.commands[0].data, vec![22, 2, 5, 168, 50]);
}

// ── parse_response: multiple command responses ──────────────────────────

#[test]
fn parse_response_multiple_commands() {
    // status=0x01 (Ready), then two command responses
    let contents = &[
        0x01, // status: Ready, Ok, no toggle
        0x80, 0x01, 0x01, // GetStatus → 1 byte
        0x91, 0x05, 22, 2, 5, 168, 50, // GetVersion → 5 bytes
    ];
    let resp = parse_response(contents).unwrap();
    assert_eq!(resp.commands.len(), 2);
    assert_eq!(resp.commands[0].command_id, 0x80);
    assert_eq!(resp.commands[0].data, vec![0x01]);
    assert_eq!(resp.commands[1].command_id, 0x91);
    assert_eq!(resp.commands[1].data, vec![22, 2, 5, 168, 50]);
}

#[test]
fn parse_response_mixed_zero_and_nonzero_data() {
    // GoIdle (no data) + GetStatus (1 byte)
    let contents = &[
        0x02, // status: Idle
        0x82, 0x00, // GoIdle → 0 bytes
        0x80, 0x01, 0x02, // GetStatus → 1 byte
    ];
    let resp = parse_response(contents).unwrap();
    assert_eq!(resp.commands.len(), 2);
    assert_eq!(resp.commands[0].command_id, 0x82);
    assert!(resp.commands[0].data.is_empty());
    assert_eq!(resp.commands[1].command_id, 0x80);
    assert_eq!(resp.commands[1].data, vec![0x02]);
}

// ── parse_response: wrapper command responses ───────────────────────────

#[test]
fn parse_response_wrapper_contains_sub_responses() {
    // GetPmCfg wrapper response: the wrapper's data holds nested sub-responses.
    let contents = &[
        0x01, // status: Ready
        0x7E, 0x06, // GetPmCfg wrapper, 6 data bytes
        0x80, 0x02, 0x01, 0x23, // sub: FwVersion → 2 bytes
        0x81, 0x00, // sub: HwVersion → 0 bytes (empty)
    ];
    let resp = parse_response(contents).unwrap();
    assert_eq!(resp.commands.len(), 1);
    assert_eq!(resp.commands[0].command_id, 0x7E);
    assert_eq!(resp.commands[0].data.len(), 6);

    // Parse sub-responses from the wrapper data.
    let subs = parse_command_responses(&resp.commands[0].data).unwrap();
    assert_eq!(subs.len(), 2);
    assert_eq!(subs[0].command_id, 0x80);
    assert_eq!(subs[0].data, vec![0x01, 0x23]);
    assert_eq!(subs[1].command_id, 0x81);
    assert!(subs[1].data.is_empty());
}

// ── parse_command_responses: edge cases ─────────────────────────────────

#[test]
fn parse_command_responses_empty() {
    let commands = parse_command_responses(&[]).unwrap();
    assert!(commands.is_empty());
}

#[test]
fn parse_command_responses_truncated_no_byte_count() {
    // command_id present but no byte count
    assert_eq!(
        parse_command_responses(&[0x80]),
        Err(ResponseError::TruncatedCommand { position: 0 })
    );
}

#[test]
fn parse_command_responses_insufficient_data() {
    // command_id=0x91, byte_count=5, but only 3 data bytes
    assert_eq!(
        parse_command_responses(&[0x91, 0x05, 0x01, 0x02, 0x03]),
        Err(ResponseError::InsufficientData {
            command_id: 0x91,
            expected: 5,
            available: 3,
        })
    );
}

#[test]
fn parse_command_responses_truncated_mid_sequence() {
    // First command OK, second truncated
    let data = &[
        0x80, 0x01, 0x01, // valid: cmd 0x80, 1 byte
        0x91, // truncated: cmd 0x91, no byte count
    ];
    assert_eq!(
        parse_command_responses(data),
        Err(ResponseError::TruncatedCommand { position: 3 })
    );
}

// ── parse_response: error propagation ───────────────────────────────────

#[test]
fn parse_response_invalid_status_propagates() {
    // 0x04 in low nibble → invalid server state
    assert_eq!(
        parse_response(&[0x04]),
        Err(ResponseError::InvalidServerState { value: 0x04 })
    );
}

#[test]
fn parse_response_truncated_command_propagates() {
    // Valid status, then truncated command
    assert_eq!(
        parse_response(&[0x01, 0x80]),
        Err(ResponseError::TruncatedCommand { position: 0 })
    );
}

#[test]
fn parse_response_insufficient_data_propagates() {
    // Valid status, command claims 3 bytes but only 1 available
    assert_eq!(
        parse_response(&[0x01, 0x91, 0x03, 0xAA]),
        Err(ResponseError::InsufficientData {
            command_id: 0x91,
            expected: 3,
            available: 1,
        })
    );
}

// ── Display impls ───────────────────────────────────────────────────────

#[test]
fn response_error_display() {
    assert_eq!(
        ResponseError::Empty.to_string(),
        "response frame contents are empty"
    );
    assert_eq!(
        ResponseError::InvalidServerState { value: 0x04 }.to_string(),
        "invalid server state value: 0x04"
    );
    assert_eq!(
        ResponseError::TruncatedCommand { position: 3 }.to_string(),
        "truncated command response at byte 3"
    );
    assert_eq!(
        ResponseError::InsufficientData {
            command_id: 0x91,
            expected: 5,
            available: 2,
        }
        .to_string(),
        "command 0x91 expects 5 data bytes, only 2 available"
    );
}

// ── Round-trip: encode commands → build frame → parse frame → parse response

#[test]
fn round_trip_encode_then_parse_status_only() {
    use crate::framing::{build_standard_frame, parse_standard_frame};

    // Simulate a PM response: status byte only (Idle, Ok, no toggle)
    let response_contents = &[0x02];
    let frame = build_standard_frame(response_contents).unwrap();
    let parsed_contents = parse_standard_frame(&frame).unwrap();
    let resp = parse_response(&parsed_contents).unwrap();

    assert_eq!(resp.status.server_state, ServerState::Idle);
    assert!(resp.commands.is_empty());
}

#[test]
fn round_trip_encode_then_parse_with_commands() {
    use crate::framing::{build_standard_frame, parse_standard_frame};

    // Simulate PM response: Ready + GetVersion response
    let response_contents = &[
        0x01, // status: Ready
        0x91, 0x05, 22, 2, 5, 168, 50, // GetVersion → 5 bytes
    ];
    let frame = build_standard_frame(response_contents).unwrap();
    let parsed_contents = parse_standard_frame(&frame).unwrap();
    let resp = parse_response(&parsed_contents).unwrap();

    assert_eq!(resp.status.server_state, ServerState::Ready);
    assert_eq!(resp.commands.len(), 1);
    assert_eq!(resp.commands[0].command_id, 0x91);
    assert_eq!(resp.commands[0].data, vec![22, 2, 5, 168, 50]);
}

// ── Realistic scenario tests ────────────────────────────────────────────

#[test]
fn realistic_get_status_response() {
    // A typical GetStatus response from PM5 in Idle state
    let contents = &[0x02, 0x80, 0x01, 0x02];
    let resp = parse_response(contents).unwrap();
    assert_eq!(resp.status.server_state, ServerState::Idle);
    assert_eq!(resp.status.prev_frame_status, PrevFrameStatus::Ok);
    assert_eq!(resp.commands[0].command_id, 0x80);
    assert_eq!(resp.commands[0].data, vec![0x02]); // status echo
}

#[test]
fn realistic_multi_command_response() {
    // GetStatus + GetVersion + GetSerial in a single frame response
    let contents = &[
        0x81, // status: Ready, toggle=1
        0x80, 0x01, 0x01, // GetStatus → status echo
        0x91, 0x05, 22, 2, 5, 168, 50, // GetVersion
        0x94, 0x09, b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'9', // GetSerial
    ];
    let resp = parse_response(contents).unwrap();
    assert!(resp.status.frame_toggle);
    assert_eq!(resp.status.server_state, ServerState::Ready);
    assert_eq!(resp.commands.len(), 3);
    assert_eq!(resp.commands[2].command_id, 0x94);
    assert_eq!(resp.commands[2].data, b"123456789".to_vec());
}

#[test]
fn realistic_wrapper_get_pm_cfg_response() {
    // Response to GetPmCfg { FwVersion, WorkoutState, ErgMachineType }
    let wrapper_data = &[
        0x80, 0x02, 168, 50, // FwVersion sub → 2 bytes
        0x8D, 0x01, 0x01, // WorkoutState sub → 1 byte (WorkoutRow)
        0xED, 0x01, 0x00, // ErgMachineType sub → 1 byte (StaticD)
    ];
    let mut contents = vec![0x05]; // status: InUse
    contents.push(0x7E); // GetPmCfg wrapper ID
    contents.push(wrapper_data.len() as u8);
    contents.extend_from_slice(wrapper_data);

    let resp = parse_response(&contents).unwrap();
    assert_eq!(resp.status.server_state, ServerState::InUse);
    assert_eq!(resp.commands.len(), 1);
    assert_eq!(resp.commands[0].command_id, 0x7E);

    let subs = parse_command_responses(&resp.commands[0].data).unwrap();
    assert_eq!(subs.len(), 3);
    assert_eq!(subs[0].command_id, 0x80);
    assert_eq!(subs[0].data, vec![168, 50]);
    assert_eq!(subs[1].command_id, 0x8D);
    assert_eq!(subs[1].data, vec![0x01]);
    assert_eq!(subs[2].command_id, 0xED);
    assert_eq!(subs[2].data, vec![0x00]);
}

// ── Boundary: maximum data length ───────────────────────────────────────

#[test]
fn parse_response_command_with_max_byte_count() {
    // A command response with byte_count=255 (maximum)
    let mut contents = vec![0x01]; // status: Ready
    contents.push(0x91); // command ID
    contents.push(255); // byte count
    contents.extend(vec![0xAA; 255]); // 255 data bytes

    let resp = parse_response(&contents).unwrap();
    assert_eq!(resp.commands.len(), 1);
    assert_eq!(resp.commands[0].data.len(), 255);
}
