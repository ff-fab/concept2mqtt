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
            "EXTENDED_START",
            "STANDARD_START",
            "STOP",
            "STUFF_MARKER",
            "MAX_FRAME_SIZE",
            "__version__",
            "build_extended_frame",
            "build_standard_frame",
            "compute_checksum",
            "parse_extended_frame",
            "parse_frame",
            "parse_standard_frame",
            "stuff_bytes",
            "unstuff_bytes",
            "validate_checksum",
        ],
    )
    def test_symbol_exported(self, name: str) -> None:
        assert hasattr(csafe_codec, name)
        assert name in csafe_codec.__all__
