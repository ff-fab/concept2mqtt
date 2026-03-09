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
