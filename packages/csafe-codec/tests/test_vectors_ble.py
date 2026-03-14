"""YAML-driven test vectors for BLE notification decoders.

Vectors are defined in tests/vectors/ble_decoders.yaml, derived from
docs/planning/spec/csafe/ble_services.yaml (Rev 0.25).  Each vector gives a
raw BLE notification payload and the expected decoded field values.

Test Techniques Used:
- Specification-based Testing: vectors trace directly to BLE service spec fields
- Equivalence Partitioning: one representative payload per characteristic
- Boundary Value Analysis: signed values (force curve), max belt ID (uint32)
- Round-trip Testing: bytes → decoder → field assertions for all 12 characteristics
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import csafe_codec
import pytest
import yaml

# ---------------------------------------------------------------------------
# Paths & loading
# ---------------------------------------------------------------------------

_VECTORS_PATH = Path(__file__).parent / "vectors" / "ble_decoders.yaml"

_DECODERS: dict[str, Any] = {
    "general_status": csafe_codec.decode_general_status,
    "additional_status_1": csafe_codec.decode_additional_status_1,
    "additional_status_2": csafe_codec.decode_additional_status_2,
    "stroke_data": csafe_codec.decode_stroke_data,
    "additional_stroke_data": csafe_codec.decode_additional_stroke_data,
    "split_interval_data": csafe_codec.decode_split_interval_data,
    "additional_split_interval_data": csafe_codec.decode_additional_split_interval_data,
    "end_of_workout_summary": csafe_codec.decode_end_of_workout_summary,
    "end_of_workout_additional_summary": (
        csafe_codec.decode_end_of_workout_additional_summary
    ),
    "heart_rate_belt_info": csafe_codec.decode_heart_rate_belt_info,
    "end_of_workout_additional_summary_2": (
        csafe_codec.decode_end_of_workout_additional_summary_2
    ),
    "force_curve_data": csafe_codec.decode_force_curve_data,
    "additional_status_3": csafe_codec.decode_additional_status_3,
    "logged_workout": csafe_codec.decode_logged_workout,
}


def _parse_bytes(hex_str: str) -> bytes:
    """Convert a space-separated hex string (e.g. '10 27 00') to bytes."""
    tokens = re.sub(r"\s+", " ", hex_str.strip()).split()
    return bytes(int(t, 16) for t in tokens)


def _load_vectors() -> list[tuple[str, str, bytes, dict[str, Any]]]:
    """Return a flat list of (characteristic, id, payload, expected) tuples."""
    raw = yaml.safe_load(_VECTORS_PATH.read_text())
    cases: list[tuple[str, str, bytes, dict[str, Any]]] = []
    for char, vectors in raw.items():
        for v in vectors:
            cases.append((char, v["id"], _parse_bytes(v["bytes"]), v["expected"]))
    return cases


_VECTORS = _load_vectors()
_IDS = [f"{char}::{vid}" for char, vid, _, _ in _VECTORS]


# ---------------------------------------------------------------------------
# Parametrized test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("char,vid,payload,expected", _VECTORS, ids=_IDS)
def test_vector_decodes_correctly(
    char: str,
    vid: str,
    payload: bytes,
    expected: dict[str, Any],
) -> None:
    """Decode payload and assert every field in the expected dict matches."""
    decoder = _DECODERS[char]
    result = decoder(payload)

    for field, want in expected.items():
        got = getattr(result, field)
        assert got == want, (
            f"{char}::{vid} field '{field}': got {got!r}, expected {want!r}"
        )


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------


def test_vectors_file_covers_all_decoders() -> None:
    """Every decoder must have at least one test vector."""
    raw = yaml.safe_load(_VECTORS_PATH.read_text())
    covered = set(raw.keys())
    required = set(_DECODERS.keys())
    missing = required - covered
    assert not missing, f"No vectors for: {sorted(missing)}"


def test_vectors_file_is_parseable() -> None:
    """Sanity check: the YAML file loads without error and is non-empty."""
    raw = yaml.safe_load(_VECTORS_PATH.read_text())
    assert isinstance(raw, dict)
    assert len(raw) > 0
