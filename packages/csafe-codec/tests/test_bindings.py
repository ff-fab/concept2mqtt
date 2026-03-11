"""Python-side tests for csafe_codec — validates PyO3 bindings and re-exports.

Test Techniques Used:
- Round-trip Testing: build → parse fidelity across the FFI boundary
- Equivalence Partitioning: normal payloads, reserved bytes, empty, oversized
- Error Guessing: invalid inputs that should raise ValueError
- Specification-based Testing: constants match protocol spec values
"""

from __future__ import annotations

import csafe_codec
import pytest

# =============================================================================
# Constants
# =============================================================================


class TestConstants:
    """Protocol constants are exposed with correct values."""

    def test_standard_start(self) -> None:
        assert csafe_codec.STANDARD_START == 0xF1
        assert isinstance(csafe_codec.STANDARD_START, int)

    def test_extended_start(self) -> None:
        assert csafe_codec.EXTENDED_START == 0xF0
        assert isinstance(csafe_codec.EXTENDED_START, int)

    def test_stop(self) -> None:
        assert csafe_codec.STOP == 0xF2
        assert isinstance(csafe_codec.STOP, int)

    def test_stuff_marker(self) -> None:
        assert csafe_codec.STUFF_MARKER == 0xF3
        assert isinstance(csafe_codec.STUFF_MARKER, int)

    def test_max_frame_size(self) -> None:
        assert csafe_codec.MAX_FRAME_SIZE == 120
        assert isinstance(csafe_codec.MAX_FRAME_SIZE, int)

    def test_version_is_set(self) -> None:
        assert isinstance(csafe_codec.__version__, str)
        assert len(csafe_codec.__version__) > 0


# =============================================================================
# Byte Stuffing
# =============================================================================


class TestStuffBytes:
    """stuff_bytes escapes reserved bytes through PyO3 boundary."""

    def test_no_reserved_bytes(self) -> None:
        assert csafe_codec.stuff_bytes(b"\x00\x42\xef\xff") == b"\x00\x42\xef\xff"

    def test_each_reserved_byte(self) -> None:
        assert csafe_codec.stuff_bytes(b"\xf0") == b"\xf3\x00"
        assert csafe_codec.stuff_bytes(b"\xf1") == b"\xf3\x01"
        assert csafe_codec.stuff_bytes(b"\xf2") == b"\xf3\x02"
        assert csafe_codec.stuff_bytes(b"\xf3") == b"\xf3\x03"

    def test_empty(self) -> None:
        assert csafe_codec.stuff_bytes(b"") == b""

    def test_returns_bytes(self) -> None:
        result = csafe_codec.stuff_bytes(b"\x42")
        assert isinstance(result, bytes)


class TestUnstuffBytes:
    """unstuff_bytes reverses escaping through PyO3 boundary."""

    def test_each_reserved_byte(self) -> None:
        assert csafe_codec.unstuff_bytes(b"\xf3\x00") == b"\xf0"
        assert csafe_codec.unstuff_bytes(b"\xf3\x01") == b"\xf1"
        assert csafe_codec.unstuff_bytes(b"\xf3\x02") == b"\xf2"
        assert csafe_codec.unstuff_bytes(b"\xf3\x03") == b"\xf3"

    def test_empty(self) -> None:
        assert csafe_codec.unstuff_bytes(b"") == b""

    def test_truncated_escape_raises(self) -> None:
        with pytest.raises(ValueError, match="truncated escape"):
            csafe_codec.unstuff_bytes(b"\xf3")

    def test_invalid_offset_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid escape offset"):
            csafe_codec.unstuff_bytes(b"\xf3\x10")


class TestStuffingRoundTrip:
    """stuff → unstuff recovers original bytes across FFI."""

    def test_all_byte_values(self) -> None:
        original = bytes(range(256))
        recovered = csafe_codec.unstuff_bytes(csafe_codec.stuff_bytes(original))
        assert recovered == original


# =============================================================================
# Checksum
# =============================================================================


class TestComputeChecksum:
    """compute_checksum returns XOR fold through PyO3 boundary."""

    def test_empty(self) -> None:
        assert csafe_codec.compute_checksum(b"") == 0x00

    def test_single_byte(self) -> None:
        assert csafe_codec.compute_checksum(b"\x42") == 0x42

    def test_multi_byte(self) -> None:
        assert csafe_codec.compute_checksum(b"\xaa\x55") == 0xFF

    def test_returns_int(self) -> None:
        result = csafe_codec.compute_checksum(b"\x42")
        assert isinstance(result, int)


class TestValidateChecksum:
    """validate_checksum returns bool through PyO3 boundary."""

    def test_correct(self) -> None:
        assert csafe_codec.validate_checksum(b"\x01\x02\x03\x04", 0x04) is True

    def test_incorrect(self) -> None:
        assert csafe_codec.validate_checksum(b"\x01\x02\x03\x04", 0x05) is False


# =============================================================================
# Frame Building
# =============================================================================


class TestBuildStandardFrame:
    """build_standard_frame produces wire-format frames through PyO3."""

    def test_single_command(self) -> None:
        frame = csafe_codec.build_standard_frame(b"\x91")
        assert frame == b"\xf1\x91\x91\xf2"

    def test_empty_contents(self) -> None:
        frame = csafe_codec.build_standard_frame(b"")
        assert frame == b"\xf1\x00\xf2"

    def test_reserved_bytes_stuffed(self) -> None:
        frame = csafe_codec.build_standard_frame(b"\xf1")
        assert frame == b"\xf1\xf3\x01\xf3\x01\xf2"

    def test_too_large_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds 120-byte limit"):
            csafe_codec.build_standard_frame(b"\x01" * 118)

    def test_returns_bytes(self) -> None:
        result = csafe_codec.build_standard_frame(b"\x42")
        assert isinstance(result, bytes)


# =============================================================================
# Frame Parsing
# =============================================================================


class TestParseStandardFrame:
    """parse_standard_frame decodes wire-format frames through PyO3."""

    def test_single_command(self) -> None:
        contents = csafe_codec.parse_standard_frame(b"\xf1\x91\x91\xf2")
        assert contents == b"\x91"

    def test_empty_contents(self) -> None:
        contents = csafe_codec.parse_standard_frame(b"\xf1\x00\xf2")
        assert contents == b""

    def test_stuffed_contents(self) -> None:
        contents = csafe_codec.parse_standard_frame(b"\xf1\xf3\x01\xf3\x01\xf2")
        assert contents == b"\xf1"

    def test_empty_frame_raises(self) -> None:
        with pytest.raises(ValueError, match="no data or checksum"):
            csafe_codec.parse_standard_frame(b"")

    def test_missing_start_raises(self) -> None:
        with pytest.raises(ValueError, match="expected start flag"):
            csafe_codec.parse_standard_frame(b"\x00\x42\x42\xf2")

    def test_missing_stop_raises(self) -> None:
        with pytest.raises(ValueError, match="expected stop flag"):
            csafe_codec.parse_standard_frame(b"\xf1\x42\x42\xff")

    def test_bad_checksum_raises(self) -> None:
        with pytest.raises(ValueError, match="checksum mismatch"):
            csafe_codec.parse_standard_frame(b"\xf1\x01\xff\xf2")

    def test_too_large_raises(self) -> None:
        frame = bytearray(121)
        frame[0] = 0xF1
        frame[-1] = 0xF2
        with pytest.raises(ValueError, match="exceeds 120-byte limit"):
            csafe_codec.parse_standard_frame(bytes(frame))


# =============================================================================
# Build → Parse Round-Trip (across FFI boundary)
# =============================================================================


class TestFrameRoundTrip:
    """Build and parse round-trip preserves data across the Python ↔ Rust boundary."""

    def test_simple_payload(self) -> None:
        original = b"\x91"
        recovered = csafe_codec.parse_standard_frame(
            csafe_codec.build_standard_frame(original)
        )
        assert recovered == original

    def test_reserved_bytes(self) -> None:
        original = b"\xf0\xf1\xf2\xf3\x42"
        recovered = csafe_codec.parse_standard_frame(
            csafe_codec.build_standard_frame(original)
        )
        assert recovered == original

    def test_all_single_bytes(self) -> None:
        """Every possible single-byte payload survives the round-trip."""
        for b in range(256):
            original = bytes([b])
            recovered = csafe_codec.parse_standard_frame(
                csafe_codec.build_standard_frame(original)
            )
            assert recovered == original, f"round-trip failed for 0x{b:02X}"

    def test_empty_payload(self) -> None:
        recovered = csafe_codec.parse_standard_frame(
            csafe_codec.build_standard_frame(b"")
        )
        assert recovered == b""


# =============================================================================
# Address Constants
# =============================================================================


class TestAddressConstants:
    """Extended-frame address constants are exposed with correct values."""

    def test_addr_pc_host(self) -> None:
        assert csafe_codec.ADDR_PC_HOST == 0x00
        assert isinstance(csafe_codec.ADDR_PC_HOST, int)

    def test_addr_default_secondary(self) -> None:
        assert csafe_codec.ADDR_DEFAULT_SECONDARY == 0xFD
        assert isinstance(csafe_codec.ADDR_DEFAULT_SECONDARY, int)

    def test_addr_reserved(self) -> None:
        assert csafe_codec.ADDR_RESERVED == 0xFE
        assert isinstance(csafe_codec.ADDR_RESERVED, int)

    def test_addr_broadcast(self) -> None:
        assert csafe_codec.ADDR_BROADCAST == 0xFF
        assert isinstance(csafe_codec.ADDR_BROADCAST, int)


# =============================================================================
# Extended Frame Building
# =============================================================================


class TestBuildExtendedFrame:
    """build_extended_frame produces wire-format extended frames through PyO3."""

    def test_simple(self) -> None:
        frame = csafe_codec.build_extended_frame(0xFD, 0x00, b"\x91")
        assert frame == b"\xf0\xfd\x00\x91\x91\xf2"

    def test_empty_contents(self) -> None:
        frame = csafe_codec.build_extended_frame(0xFD, 0x00, b"")
        assert frame == b"\xf0\xfd\x00\x00\xf2"

    def test_address_stuffing(self) -> None:
        frame = csafe_codec.build_extended_frame(0x00, 0xF1, b"\x91")
        assert frame == b"\xf0\x00\xf3\x01\x91\x91\xf2"

    def test_too_large_raises(self) -> None:
        with pytest.raises(ValueError, match="exceeds 120-byte limit"):
            csafe_codec.build_extended_frame(0x00, 0x00, b"\x01" * 116)

    def test_returns_bytes(self) -> None:
        result = csafe_codec.build_extended_frame(0x00, 0x00, b"\x42")
        assert isinstance(result, bytes)


# =============================================================================
# Extended Frame Parsing
# =============================================================================


class TestParseExtendedFrame:
    """parse_extended_frame decodes extended wire-format frames through PyO3."""

    def test_simple(self) -> None:
        dst, src, contents = csafe_codec.parse_extended_frame(
            b"\xf0\xfd\x00\x91\x91\xf2"
        )
        assert dst == 0xFD
        assert src == 0x00
        assert contents == b"\x91"

    def test_empty_contents(self) -> None:
        dst, src, contents = csafe_codec.parse_extended_frame(b"\xf0\xfd\x00\x00\xf2")
        assert contents == b""

    def test_returns_tuple(self) -> None:
        result = csafe_codec.parse_extended_frame(b"\xf0\xfd\x00\x91\x91\xf2")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_empty_frame_raises(self) -> None:
        with pytest.raises(ValueError, match="no data or checksum"):
            csafe_codec.parse_extended_frame(b"")

    def test_wrong_start_raises(self) -> None:
        with pytest.raises(ValueError, match="expected start flag"):
            csafe_codec.parse_extended_frame(b"\xf1\x00\x00\x00\xf2")

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="frame too short"):
            csafe_codec.parse_extended_frame(b"\xf0\x00\x00\xf2")

    def test_bad_checksum_raises(self) -> None:
        with pytest.raises(ValueError, match="checksum mismatch"):
            csafe_codec.parse_extended_frame(b"\xf0\x00\x00\x01\xff\xf2")


# =============================================================================
# Extended Frame Round-Trip
# =============================================================================


class TestExtendedFrameRoundTrip:
    """Build and parse round-trip for extended frames across FFI."""

    def test_simple(self) -> None:
        original = b"\x91"
        frame = csafe_codec.build_extended_frame(0xFD, 0x00, original)
        dst, src, contents = csafe_codec.parse_extended_frame(frame)
        assert dst == 0xFD
        assert src == 0x00
        assert contents == original

    def test_reserved_bytes(self) -> None:
        original = b"\xf0\xf1\xf2\xf3\x42"
        frame = csafe_codec.build_extended_frame(0xFD, 0x00, original)
        _, _, contents = csafe_codec.parse_extended_frame(frame)
        assert contents == original

    def test_reserved_addresses(self) -> None:
        frame = csafe_codec.build_extended_frame(0xF0, 0xF3, b"\x42")
        dst, src, contents = csafe_codec.parse_extended_frame(frame)
        assert dst == 0xF0
        assert src == 0xF3
        assert contents == b"\x42"


# =============================================================================
# Auto-detecting parse_frame
# =============================================================================


class TestParseFrame:
    """parse_frame auto-detects standard vs extended frames."""

    def test_standard(self) -> None:
        wire = csafe_codec.build_standard_frame(b"\x91")
        result = csafe_codec.parse_frame(wire)
        assert result["type"] == "standard"
        assert result["contents"] == b"\x91"

    def test_extended(self) -> None:
        wire = csafe_codec.build_extended_frame(0xFD, 0x00, b"\x91")
        result = csafe_codec.parse_frame(wire)
        assert result["type"] == "extended"
        assert result["destination"] == 0xFD
        assert result["source"] == 0x00
        assert result["contents"] == b"\x91"

    def test_returns_dict(self) -> None:
        wire = csafe_codec.build_standard_frame(b"\x42")
        result = csafe_codec.parse_frame(wire)
        assert isinstance(result, dict)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            csafe_codec.parse_frame(b"")


# =============================================================================
# Public API surface
# =============================================================================


class TestPublicAPI:
    """All expected symbols are accessible from the package."""

    @pytest.mark.parametrize(
        "name",
        [
            "ADDR_BROADCAST",
            "ADDR_DEFAULT_SECONDARY",
            "ADDR_PC_HOST",
            "ADDR_RESERVED",
            "CMD_GET_STATUS",
            "CMD_RESET",
            "CMD_SET_TIME",
            "CMD_GET_PM_CFG",
            "CMD_SET_USER_CFG1",
            "EXTENDED_START",
            "STANDARD_START",
            "STOP",
            "STUFF_MARKER",
            "MAX_FRAME_SIZE",
            "__version__",
            "build_extended_frame",
            "build_standard_frame",
            "compute_checksum",
            "duration_type_name",
            "duration_type_values",
            "erg_machine_type_name",
            "erg_machine_type_values",
            "interval_type_name",
            "interval_type_values",
            "parse_extended_frame",
            "parse_frame",
            "parse_standard_frame",
            "rowing_state_name",
            "rowing_state_values",
            "screen_type_name",
            "screen_type_values",
            "stroke_state_name",
            "stroke_state_values",
            "stuff_bytes",
            "unstuff_bytes",
            "validate_checksum",
            "workout_state_name",
            "workout_state_values",
            "workout_type_name",
            "workout_type_values",
        ],
    )
    def test_symbol_exported(self, name: str) -> None:
        assert hasattr(csafe_codec, name)
        assert name in csafe_codec.__all__


# =============================================================================
# Command enum bindings
# =============================================================================


class TestEnumNameLookups:
    """Enum name functions return correct names and reject invalid values."""

    @pytest.mark.parametrize(
        ("func", "value", "expected"),
        [
            ("workout_type_name", 0, "JustRowNoSplits"),
            ("interval_type_name", 255, "None"),
            ("workout_state_name", 1, "WorkoutRow"),
            ("rowing_state_name", 0, "Inactive"),
            ("stroke_state_name", 2, "Driving"),
            ("duration_type_name", 0x80, "Distance"),
            ("screen_type_name", 3, "Csafe"),
            ("erg_machine_type_name", 192, "Bike"),
        ],
    )
    def test_valid_lookup(self, func: str, value: int, expected: str) -> None:
        assert getattr(csafe_codec, func)(value) == expected

    @pytest.mark.parametrize(
        ("func", "invalid_value"),
        [
            ("workout_type_name", 99),
            ("interval_type_name", 128),
            ("workout_state_name", 200),
            ("rowing_state_name", 5),
            ("stroke_state_name", 99),
            ("duration_type_name", 0x10),
            ("screen_type_name", 99),
            ("erg_machine_type_name", 99),
        ],
    )
    def test_invalid_raises(self, func: str, invalid_value: int) -> None:
        with pytest.raises(ValueError, match="invalid"):
            getattr(csafe_codec, func)(invalid_value)


class TestEnumValuesDicts:
    """Enum values functions return complete dicts."""

    @pytest.mark.parametrize(
        ("func", "expected_count"),
        [
            ("workout_type_values", 13),
            ("interval_type_values", 11),
            ("workout_state_values", 14),
            ("rowing_state_values", 2),
            ("stroke_state_values", 5),
            ("duration_type_values", 4),
            ("screen_type_values", 6),
            ("erg_machine_type_values", 23),
        ],
    )
    def test_entry_count(self, func: str, expected_count: int) -> None:
        values = getattr(csafe_codec, func)()
        assert isinstance(values, dict)
        assert len(values) == expected_count

    def test_workout_type_values_spot_check(self) -> None:
        vals = csafe_codec.workout_type_values()
        assert vals["JustRowNoSplits"] == 0
        assert vals["FixedCalorieInterval"] == 12

    def test_interval_type_has_none_at_255(self) -> None:
        vals = csafe_codec.interval_type_values()
        assert vals["None"] == 255


class TestCommandIdConstants:
    """CMD_* constants match CSAFE spec byte values."""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            # Short commands (representative)
            ("CMD_GET_STATUS", 0x80),
            ("CMD_RESET", 0x81),
            ("CMD_GO_IDLE", 0x82),
            ("CMD_GET_VERSION", 0x91),
            ("CMD_GET_CALORIES", 0xA3),
            ("CMD_GET_HEART_RATE", 0xB0),
            # Long commands (representative)
            ("CMD_AUTO_UPLOAD", 0x01),
            ("CMD_SET_TIME", 0x11),
            ("CMD_SET_PROGRAM", 0x24),
            ("CMD_GET_CAPS", 0x70),
            # PM wrapper commands
            ("CMD_SET_USER_CFG1", 0x1A),
            ("CMD_SET_PM_CFG", 0x76),
            ("CMD_SET_PM_DATA", 0x77),
            ("CMD_GET_PM_CFG", 0x7E),
            ("CMD_GET_PM_DATA", 0x7F),
        ],
    )
    def test_constant_value(self, name: str, expected: int) -> None:
        assert getattr(csafe_codec, name) == expected


# =============================================================================
# GetPmCfgCommand — factory methods and encoding
# =============================================================================


class TestGetPmCfgCommandFactories:
    """GetPmCfgCommand factory methods return correct sub-commands.

    Test Techniques Used:
    - Specification-based Testing: factory method names and IDs match CSAFE spec
    - Equivalence Partitioning: short commands (unit) vs long commands (struct)
    """

    @pytest.mark.parametrize(
        ("method", "expected_id"),
        [
            ("fw_version", 0x80),
            ("hw_version", 0x81),
            ("hw_address", 0x82),
            ("tick_timebase", 0x83),
            ("hrm", 0x84),
            ("workout_type", 0x89),
            ("workout_state", 0x8D),
            ("rowing_state", 0x93),
            ("battery_level_percent", 0x97),
            ("workout_duration", 0xE8),
            ("flywheel_speed", 0xEC),
            ("erg_machine_type", 0xED),
        ],
    )
    def test_short_command_id(self, method: str, expected_id: int) -> None:
        cmd = getattr(csafe_codec.GetPmCfgCommand, method)()
        assert cmd.id() == expected_id

    @pytest.mark.parametrize(
        ("method", "kwargs", "expected_id"),
        [
            ("erg_number", {"hw_address": 0}, 0x50),
            ("erg_number_request", {"logical_erg_number": 1}, 0x51),
            ("user_id_string", {"user_number": 0}, 0x52),
            ("user_id", {"user_number": 0}, 0x54),
            ("user_profile", {"user_number": 0}, 0x55),
            ("hr_belt_info", {"user_number": 0}, 0x56),
            ("extended_hr_belt_info", {"user_number": 0}, 0x57),
            (
                "current_log_structure",
                {"structure_id": 0, "split_interval_number": 0},
                0x58,
            ),
        ],
    )
    def test_struct_command_id(
        self, method: str, kwargs: dict, expected_id: int
    ) -> None:
        cmd = getattr(csafe_codec.GetPmCfgCommand, method)(**kwargs)
        assert cmd.id() == expected_id

    def test_returns_correct_type(self) -> None:
        cmd = csafe_codec.GetPmCfgCommand.fw_version()
        assert type(cmd).__name__ == "GetPmCfgCommand"


class TestGetPmCfgCommandEncoding:
    """GetPmCfgCommand encoding produces correct wire bytes.

    Test Techniques Used:
    - Round-trip Testing: Python encode matches known Rust encoding
    - Specification-based Testing: wire format matches CSAFE protocol
    """

    def test_short_command_encodes_single_byte(self) -> None:
        cmd = csafe_codec.GetPmCfgCommand.fw_version()
        assert cmd.encode() == bytes([0x80])

    def test_short_command_returns_bytes(self) -> None:
        assert isinstance(csafe_codec.GetPmCfgCommand.fw_version().encode(), bytes)

    def test_erg_number_with_address(self) -> None:
        cmd = csafe_codec.GetPmCfgCommand.erg_number(hw_address=0x12345678)
        assert cmd.encode() == bytes([0x50, 4, 0x78, 0x56, 0x34, 0x12])

    def test_erg_number_request(self) -> None:
        cmd = csafe_codec.GetPmCfgCommand.erg_number_request(logical_erg_number=5)
        assert cmd.encode() == bytes([0x51, 1, 5])

    def test_current_log_structure(self) -> None:
        cmd = csafe_codec.GetPmCfgCommand.current_log_structure(
            structure_id=2,
            split_interval_number=3,
        )
        assert cmd.encode() == bytes([0x58, 2, 2, 3])


# =============================================================================
# GetPmDataCommand — factory methods and encoding
# =============================================================================


class TestGetPmDataCommandFactories:
    """GetPmDataCommand factory methods return correct sub-commands.

    Test Techniques Used:
    - Specification-based Testing: factory names and IDs from PM data spec
    - Equivalence Partitioning: short (unit) vs long (struct) sub-commands
    """

    @pytest.mark.parametrize(
        ("method", "expected_id"),
        [
            ("work_time", 0xA0),
            ("work_distance", 0xA3),
            ("stroke_500m_pace", 0xA8),
            ("stroke_power", 0xA9),
            ("stroke_rate", 0xB3),
            ("avg_heart_rate", 0xB6),
            ("drag_factor", 0xC1),
            ("sync_data", 0xC4),
            ("rest_time", 0xCF),
        ],
    )
    def test_short_command_id(self, method: str, expected_id: int) -> None:
        cmd = getattr(csafe_codec.GetPmDataCommand, method)()
        assert cmd.id() == expected_id

    @pytest.mark.parametrize(
        ("method", "kwargs", "expected_id"),
        [
            ("memory", {"device_type": 0, "start_address": 0, "block_length": 1}, 0x68),
            ("log_card_memory", {"start_address": 0, "block_length": 1}, 0x69),
            ("internal_log_memory", {"start_address": 0, "block_length": 1}, 0x6A),
            ("force_plot_data", {"block_length": 32}, 0x6B),
            ("heartbeat_data", {"block_length": 16}, 0x6C),
            ("stroke_stats", {"unused": 0}, 0x6E),
            ("diag_log_record_num", {"record_type": 1}, 0x70),
        ],
    )
    def test_struct_command_id(
        self, method: str, kwargs: dict, expected_id: int
    ) -> None:
        cmd = getattr(csafe_codec.GetPmDataCommand, method)(**kwargs)
        assert cmd.id() == expected_id


class TestGetPmDataCommandEncoding:
    """GetPmDataCommand encoding produces correct wire bytes.

    Test Techniques Used:
    - Round-trip Testing: Python encode matches Rust encoding
    """

    def test_short_command_encode(self) -> None:
        assert csafe_codec.GetPmDataCommand.work_time().encode() == bytes([0xA0])

    def test_memory_command(self) -> None:
        cmd = csafe_codec.GetPmDataCommand.memory(
            device_type=1,
            start_address=0x100,
            block_length=32,
        )
        expected = bytes([0x68, 6, 1]) + (0x100).to_bytes(4, "little") + bytes([32])
        assert cmd.encode() == expected

    def test_force_plot_data(self) -> None:
        cmd = csafe_codec.GetPmDataCommand.force_plot_data(block_length=32)
        assert cmd.encode() == bytes([0x6B, 1, 32])

    def test_diag_log_record(self) -> None:
        cmd = csafe_codec.GetPmDataCommand.diag_log_record(
            record_type=2,
            record_index=10,
            record_offset_bytes=100,
        )
        expected = (
            bytes([0x71, 5, 2])
            + (10).to_bytes(2, "little")
            + (100).to_bytes(2, "little")
        )
        assert cmd.encode() == expected


# =============================================================================
# SetPmCfgCommand — factory methods and encoding
# =============================================================================


class TestSetPmCfgCommandFactories:
    """SetPmCfgCommand factory methods return correct sub-commands.

    Test Techniques Used:
    - Specification-based Testing: factory names and IDs from PM config spec
    - Equivalence Partitioning: unit (reset_erg_number) vs struct commands
    """

    def test_reset_erg_number_is_short(self) -> None:
        cmd = csafe_codec.SetPmCfgCommand.reset_erg_number()
        assert cmd.id() == 0xE1

    @pytest.mark.parametrize(
        ("method", "kwargs", "expected_id"),
        [
            ("workout_type", {"workout_type": 0}, 0x01),
            ("workout_duration", {"duration_type": 0, "duration": 0}, 0x03),
            ("rest_duration", {"duration": 0}, 0x04),
            ("split_duration", {"duration_type": 0, "duration": 0}, 0x05),
            ("target_pace_time", {"pace_time": 0}, 0x06),
            ("race_type", {"race_type": 0}, 0x09),
            ("erg_number", {"hw_address": 0, "erg_number": 0}, 0x10),
            ("screen_state", {"screen_type": 0, "screen_value": 0}, 0x13),
            ("configure_workout", {"programming_mode": 0}, 0x14),
            ("interval_type", {"interval_type": 0}, 0x17),
            (
                "date_time",
                {
                    "hours": 0,
                    "minutes": 0,
                    "meridiem": 0,
                    "month": 0,
                    "day": 0,
                    "year": 0,
                },
                0x22,
            ),
        ],
    )
    def test_struct_command_id(
        self, method: str, kwargs: dict, expected_id: int
    ) -> None:
        cmd = getattr(csafe_codec.SetPmCfgCommand, method)(**kwargs)
        assert cmd.id() == expected_id


class TestSetPmCfgCommandEncoding:
    """SetPmCfgCommand encoding produces correct wire bytes.

    Test Techniques Used:
    - Round-trip Testing: Python encode matches Rust encoding
    - Specification-based Testing: payload layout matches protocol
    """

    def test_reset_erg_number_single_byte(self) -> None:
        assert csafe_codec.SetPmCfgCommand.reset_erg_number().encode() == bytes([0xE1])

    def test_workout_type(self) -> None:
        cmd = csafe_codec.SetPmCfgCommand.workout_type(workout_type=5)
        assert cmd.encode() == bytes([0x01, 1, 5])

    def test_workout_duration(self) -> None:
        cmd = csafe_codec.SetPmCfgCommand.workout_duration(
            duration_type=0x00,
            duration=1200,
        )
        expected = bytes([0x03, 5, 0x00]) + (1200).to_bytes(4, "little")
        assert cmd.encode() == expected

    def test_rest_duration(self) -> None:
        cmd = csafe_codec.SetPmCfgCommand.rest_duration(duration=120)
        expected = bytes([0x04, 2]) + (120).to_bytes(2, "little")
        assert cmd.encode() == expected

    def test_date_time(self) -> None:
        cmd = csafe_codec.SetPmCfgCommand.date_time(
            hours=14,
            minutes=30,
            meridiem=0,
            month=6,
            day=15,
            year=2025,
        )
        expected = bytes([0x22, 7, 14, 30, 0, 6, 15]) + (2025).to_bytes(2, "little")
        assert cmd.encode() == expected

    def test_erg_number(self) -> None:
        cmd = csafe_codec.SetPmCfgCommand.erg_number(
            hw_address=0xAABBCCDD, erg_number=3
        )
        expected = bytes([0x10, 5]) + (0xAABBCCDD).to_bytes(4, "little") + bytes([3])
        assert cmd.encode() == expected

    def test_screen_state(self) -> None:
        cmd = csafe_codec.SetPmCfgCommand.screen_state(screen_type=1, screen_value=2)
        assert cmd.encode() == bytes([0x13, 2, 1, 2])


# =============================================================================
# SetPmDataCommand — factory methods and encoding
# =============================================================================


class TestSetPmDataCommandFactories:
    """SetPmDataCommand factory methods return correct sub-commands.

    Test Techniques Used:
    - Specification-based Testing: factory names and IDs from PM data spec
    - Equivalence Partitioning: short (sync) vs long (struct) sub-commands
    """

    @pytest.mark.parametrize(
        ("method", "expected_id"),
        [
            ("sync_distance", 0xD0),
            ("sync_stroke_pace", 0xD1),
            ("sync_avg_heart_rate", 0xD2),
            ("sync_time", 0xD3),
            ("sync_race_tick_time", 0xD7),
            ("sync_data_all", 0xD8),
            ("sync_rowing_active_time", 0xD9),
        ],
    )
    def test_short_command_id(self, method: str, expected_id: int) -> None:
        cmd = getattr(csafe_codec.SetPmDataCommand, method)()
        assert cmd.id() == expected_id

    @pytest.mark.parametrize(
        ("method", "kwargs", "expected_id"),
        [
            ("race_participant", {"racer_id": 1, "racer_name": b"Bob"}, 0x32),
            ("display_string", {"characters": b"Hi"}, 0x35),
            ("led_backlight", {"state": 1, "intensity": 128}, 0x3B),
            ("wireless_channel_config", {"channel_bitmask": 0xFF}, 0x3D),
        ],
    )
    def test_struct_command_id(
        self, method: str, kwargs: dict, expected_id: int
    ) -> None:
        cmd = getattr(csafe_codec.SetPmDataCommand, method)(**kwargs)
        assert cmd.id() == expected_id


class TestSetPmDataCommandEncoding:
    """SetPmDataCommand encoding produces correct wire bytes.

    Test Techniques Used:
    - Round-trip Testing: Python encode matches Rust encoding
    """

    def test_short_command_encode(self) -> None:
        assert csafe_codec.SetPmDataCommand.sync_distance().encode() == bytes([0xD0])

    def test_race_participant(self) -> None:
        cmd = csafe_codec.SetPmDataCommand.race_participant(
            racer_id=1,
            racer_name=b"Bob",
        )
        assert cmd.encode() == bytes([0x32, 4, 1]) + b"Bob"

    def test_display_string(self) -> None:
        cmd = csafe_codec.SetPmDataCommand.display_string(characters=b"Hello")
        assert cmd.encode() == bytes([0x35, 5]) + b"Hello"

    def test_led_backlight(self) -> None:
        cmd = csafe_codec.SetPmDataCommand.led_backlight(state=1, intensity=200)
        assert cmd.encode() == bytes([0x3B, 2, 1, 200])

    def test_wireless_channel_config(self) -> None:
        cmd = csafe_codec.SetPmDataCommand.wireless_channel_config(
            channel_bitmask=0xDEAD
        )
        expected = bytes([0x3D, 4]) + (0xDEAD).to_bytes(4, "little")
        assert cmd.encode() == expected


# =============================================================================
# SetUserCfg1Command — factory methods and encoding
# =============================================================================


class TestSetUserCfg1CommandFactories:
    """SetUserCfg1Command factory methods return correct sub-commands.

    Test Techniques Used:
    - Specification-based Testing: all 6 factory methods match restricted subset
    """

    @pytest.mark.parametrize(
        ("method", "kwargs", "expected_id"),
        [
            ("workout_type", {"workout_type": 0}, 0x01),
            ("workout_duration", {"duration_type": 0, "duration": 0}, 0x03),
            ("split_duration", {"duration_type": 0, "duration": 0}, 0x05),
            ("configure_workout", {"programming_mode": 0}, 0x14),
            ("interval_type", {"interval_type": 0}, 0x17),
            ("workout_interval_count", {"interval_count": 0}, 0x18),
        ],
    )
    def test_command_id(self, method: str, kwargs: dict, expected_id: int) -> None:
        cmd = getattr(csafe_codec.SetUserCfg1Command, method)(**kwargs)
        assert cmd.id() == expected_id


class TestSetUserCfg1CommandEncoding:
    """SetUserCfg1Command encoding produces correct wire bytes.

    Test Techniques Used:
    - Round-trip Testing: Python encode matches Rust encoding
    """

    def test_workout_type(self) -> None:
        cmd = csafe_codec.SetUserCfg1Command.workout_type(workout_type=2)
        assert cmd.encode() == bytes([0x01, 1, 2])

    def test_workout_duration(self) -> None:
        cmd = csafe_codec.SetUserCfg1Command.workout_duration(
            duration_type=0x80,
            duration=5000,
        )
        expected = bytes([0x03, 5, 0x80]) + (5000).to_bytes(4, "little")
        assert cmd.encode() == expected

    def test_workout_interval_count(self) -> None:
        cmd = csafe_codec.SetUserCfg1Command.workout_interval_count(interval_count=8)
        assert cmd.encode() == bytes([0x18, 1, 8])


# =============================================================================
# Command (public) — factory methods
# =============================================================================


class TestCommandFactories:
    """Command factory methods return correct command objects.

    Test Techniques Used:
    - Specification-based Testing: short/long/wrapper IDs match CSAFE spec
    - Equivalence Partitioning: short, long (struct), and wrapper variants
    """

    @pytest.mark.parametrize(
        ("method", "expected_id"),
        [
            ("get_status", 0x80),
            ("reset", 0x81),
            ("go_idle", 0x82),
            ("go_have_id", 0x83),
            ("go_in_use", 0x85),
            ("go_finished", 0x86),
            ("go_ready", 0x87),
            ("bad_id", 0x88),
            ("get_version", 0x91),
            ("get_id", 0x92),
            ("get_serial", 0x94),
            ("get_calories", 0xA3),
            ("get_heart_rate", 0xB0),
            ("get_power", 0xB4),
        ],
    )
    def test_short_command_id(self, method: str, expected_id: int) -> None:
        cmd = getattr(csafe_codec.Command, method)()
        assert cmd.id() == expected_id

    @pytest.mark.parametrize(
        ("method", "kwargs", "expected_id"),
        [
            ("auto_upload", {"configuration": 0}, 0x01),
            ("id_digits", {"count": 4}, 0x10),
            ("set_time", {"hour": 12, "minute": 0, "second": 0}, 0x11),
            ("set_date", {"year": 25, "month": 3, "day": 11}, 0x12),
            ("set_timeout", {"timeout": 30}, 0x13),
            ("set_twork", {"hours": 0, "minutes": 30, "seconds": 0}, 0x20),
            ("set_program", {"program": 0, "unused": 0}, 0x24),
            ("get_caps", {"capability_code": 1}, 0x70),
        ],
    )
    def test_long_command_id(self, method: str, kwargs: dict, expected_id: int) -> None:
        cmd = getattr(csafe_codec.Command, method)(**kwargs)
        assert cmd.id() == expected_id

    @pytest.mark.parametrize(
        ("method", "wrapper_id"),
        [
            ("set_user_cfg1", 0x1A),
            ("set_pm_cfg", 0x76),
            ("set_pm_data", 0x77),
            ("get_pm_cfg", 0x7E),
            ("get_pm_data", 0x7F),
        ],
    )
    def test_wrapper_command_id(self, method: str, wrapper_id: int) -> None:
        cmd = getattr(csafe_codec.Command, method)([])
        assert cmd.id() == wrapper_id


# =============================================================================
# Command encoding
# =============================================================================


class TestCommandEncoding:
    """Command encoding produces expected wire bytes.

    Test Techniques Used:
    - Round-trip Testing: Python encode matches known Rust test vectors
    - Specification-based Testing: wire format matches CSAFE protocol
    """

    def test_short_command_single_byte(self) -> None:
        assert csafe_codec.Command.get_status().encode() == bytes([0x80])

    def test_auto_upload(self) -> None:
        cmd = csafe_codec.Command.auto_upload(configuration=0x03)
        assert cmd.encode() == bytes([0x01, 0x01, 0x03])

    def test_set_time(self) -> None:
        cmd = csafe_codec.Command.set_time(hour=14, minute=30, second=45)
        assert cmd.encode() == bytes([0x11, 0x03, 14, 30, 45])

    def test_set_date(self) -> None:
        cmd = csafe_codec.Command.set_date(year=25, month=3, day=11)
        assert cmd.encode() == bytes([0x12, 0x03, 25, 3, 11])

    def test_set_calories(self) -> None:
        cmd = csafe_codec.Command.set_calories(calories_lsb=0xE8, calories_msb=0x03)
        assert cmd.encode() == bytes([0x23, 0x02, 0xE8, 0x03])

    def test_get_caps(self) -> None:
        cmd = csafe_codec.Command.get_caps(capability_code=0x01)
        assert cmd.encode() == bytes([0x70, 0x01, 0x01])


# =============================================================================
# Wrapper command encoding
# =============================================================================


class TestWrapperCommandEncoding:
    """Wrapper commands encode opcode + length + concatenated sub-commands.

    Test Techniques Used:
    - Integration Testing: wrapper encapsulates proprietary sub-commands
    - Specification-based Testing: wrapper layout matches C2 PM protocol
    """

    def test_get_pm_cfg_with_sub_commands(self) -> None:
        fw = csafe_codec.GetPmCfgCommand.fw_version()
        wt = csafe_codec.GetPmCfgCommand.workout_type()
        cmd = csafe_codec.Command.get_pm_cfg([fw, wt])
        encoded = cmd.encode()
        assert encoded[0] == 0x7E  # wrapper opcode
        assert encoded[1] == 2  # payload length (2 short sub-cmds)
        assert encoded[2] == 0x80  # FwVersion
        assert encoded[3] == 0x89  # WorkoutType

    def test_get_pm_cfg_empty(self) -> None:
        cmd = csafe_codec.Command.get_pm_cfg([])
        assert cmd.encode() == bytes([0x7E, 0x00])

    def test_get_pm_data_with_sub_commands(self) -> None:
        wt = csafe_codec.GetPmDataCommand.work_time()
        dr = csafe_codec.GetPmDataCommand.drag_factor()
        cmd = csafe_codec.Command.get_pm_data([wt, dr])
        encoded = cmd.encode()
        assert encoded == bytes([0x7F, 0x02, 0xA0, 0xC1])

    def test_set_pm_cfg_with_struct_sub(self) -> None:
        sub = csafe_codec.SetPmCfgCommand.workout_type(workout_type=5)
        cmd = csafe_codec.Command.set_pm_cfg([sub])
        encoded = cmd.encode()
        assert encoded == bytes([0x76, 3, 0x01, 1, 5])

    def test_set_pm_data_with_short_sub(self) -> None:
        sub = csafe_codec.SetPmDataCommand.sync_distance()
        cmd = csafe_codec.Command.set_pm_data([sub])
        assert cmd.encode() == bytes([0x77, 1, 0xD0])

    def test_set_user_cfg1_with_sub_commands(self) -> None:
        wt = csafe_codec.SetUserCfg1Command.workout_type(workout_type=4)
        ic = csafe_codec.SetUserCfg1Command.workout_interval_count(interval_count=3)
        cmd = csafe_codec.Command.set_user_cfg1([wt, ic])
        encoded = cmd.encode()
        assert encoded == bytes([0x1A, 6, 0x01, 1, 4, 0x18, 1, 3])

    def test_wrapper_with_long_sub_command(self) -> None:
        sub = csafe_codec.GetPmCfgCommand.erg_number(hw_address=0x01020304)
        cmd = csafe_codec.Command.get_pm_cfg([sub])
        encoded = cmd.encode()
        # 0x7E, len=6, then ErgNumber: 0x50, 4, 04, 03, 02, 01
        assert encoded == bytes([0x7E, 6, 0x50, 4, 0x04, 0x03, 0x02, 0x01])


# =============================================================================
# Top-level encode_commands and build_command_frame
# =============================================================================


class TestEncodeFunctions:
    """encode_commands and build_command_frame produce correct output.

    Test Techniques Used:
    - Round-trip Testing: encode then parse standard frame
    - Integration Testing: combines command encoding with framing
    """

    def test_encode_commands_single(self) -> None:
        result = csafe_codec.encode_commands([csafe_codec.Command.get_status()])
        assert result == bytes([0x80])

    def test_encode_commands_multiple(self) -> None:
        cmds = [csafe_codec.Command.get_status(), csafe_codec.Command.get_version()]
        result = csafe_codec.encode_commands(cmds)
        assert result == bytes([0x80, 0x91])

    def test_encode_commands_empty(self) -> None:
        assert csafe_codec.encode_commands([]) == b""

    def test_encode_commands_returns_bytes(self) -> None:
        result = csafe_codec.encode_commands([csafe_codec.Command.get_status()])
        assert isinstance(result, bytes)

    def test_encode_commands_long(self) -> None:
        cmd = csafe_codec.Command.set_time(hour=10, minute=30, second=0)
        result = csafe_codec.encode_commands([cmd])
        assert result == bytes([0x11, 0x03, 10, 30, 0])

    def test_encode_commands_mixed(self) -> None:
        cmds = [
            csafe_codec.Command.get_status(),
            csafe_codec.Command.set_timeout(timeout=5),
        ]
        result = csafe_codec.encode_commands(cmds)
        assert result == bytes([0x80, 0x13, 0x01, 5])

    def test_build_command_frame_roundtrip(self) -> None:
        cmds = [csafe_codec.Command.get_status()]
        frame = csafe_codec.build_command_frame(cmds)
        parsed = csafe_codec.parse_standard_frame(frame)
        assert parsed == bytes([0x80])

    def test_build_command_frame_returns_bytes(self) -> None:
        frame = csafe_codec.build_command_frame([csafe_codec.Command.get_status()])
        assert isinstance(frame, bytes)

    def test_build_command_frame_multiple_roundtrip(self) -> None:
        cmds = [csafe_codec.Command.get_status(), csafe_codec.Command.get_version()]
        frame = csafe_codec.build_command_frame(cmds)
        parsed = csafe_codec.parse_standard_frame(frame)
        assert parsed == bytes([0x80, 0x91])

    def test_build_command_frame_with_wrapper(self) -> None:
        fw = csafe_codec.GetPmCfgCommand.fw_version()
        cmd = csafe_codec.Command.get_pm_cfg([fw])
        frame = csafe_codec.build_command_frame([cmd])
        parsed = csafe_codec.parse_standard_frame(frame)
        assert parsed == bytes([0x7E, 0x01, 0x80])

    def test_build_command_frame_empty(self) -> None:
        frame = csafe_codec.build_command_frame([])
        parsed = csafe_codec.parse_standard_frame(frame)
        assert parsed == b""


# =============================================================================
# repr / str tests
# =============================================================================


class TestCommandRepr:
    """__repr__ and __str__ return meaningful debug strings.

    Test Techniques Used:
    - Error Guessing: verify repr contains variant name and field values
    """

    def test_repr_short_command(self) -> None:
        cmd = csafe_codec.GetPmCfgCommand.fw_version()
        assert "FwVersion" in repr(cmd)

    def test_repr_struct_command(self) -> None:
        cmd = csafe_codec.GetPmCfgCommand.erg_number(hw_address=42)
        assert "ErgNumber" in repr(cmd)
        assert "42" in repr(cmd)

    def test_str_equals_repr(self) -> None:
        cmd = csafe_codec.GetPmCfgCommand.fw_version()
        assert str(cmd) == repr(cmd)

    def test_repr_public_short(self) -> None:
        cmd = csafe_codec.Command.get_status()
        assert "GetStatus" in repr(cmd)

    def test_repr_public_long(self) -> None:
        cmd = csafe_codec.Command.set_time(hour=10, minute=30, second=0)
        assert "SetTime" in repr(cmd)

    def test_repr_set_pm_data(self) -> None:
        cmd = csafe_codec.SetPmDataCommand.sync_distance()
        assert "SyncDistance" in repr(cmd)

    def test_repr_set_user_cfg1(self) -> None:
        cmd = csafe_codec.SetUserCfg1Command.workout_type(workout_type=3)
        assert "WorkoutType" in repr(cmd)
        assert "3" in repr(cmd)
