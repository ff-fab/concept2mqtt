"""Unit tests for concept2mqtt/app.py — cosalette application scaffold.

Test Techniques Used:
- Specification-based Testing: create_app factory, adapter registration,
  payload conversion
- Equivalence Partitioning: with/without adapter class
"""

from __future__ import annotations

import pytest

from concept2mqtt.app import _status_payload, _stroke_payload, create_app
from concept2mqtt.mqtt.topics import APP_NAME
from concept2mqtt.pm5.fake import FakePm5Adapter
from concept2mqtt.pm5.port import Pm5Port
from concept2mqtt.pm5.types import (
    Pm5Status,
    Pm5Stroke,
    RowingState,
    WorkoutState,
)

# =============================================================================
# create_app
# =============================================================================


class TestCreateApp:
    """create_app() builds a configured cosalette App.

    Technique: Specification-based Testing — factory contract.
    """

    def test_app_name(self) -> None:
        app = create_app()
        assert app.name == APP_NAME

    def test_app_version(self) -> None:
        app = create_app(version="1.2.3")
        assert app.version == "1.2.3"

    def test_pm5_device_registered(self) -> None:
        """The pm5 device handler is registered on the app."""
        app = create_app()
        assert "pm5" in app.registered_names

    def test_adapter_registered_via_factory(self) -> None:
        """When a factory callable is provided, it's registered for Pm5Port.

        FakePm5Adapter has generic type annotations in __init__ that
        cosalette's DI cannot introspect, so we register a zero-arg factory.
        """
        app = create_app(adapter_class=lambda: FakePm5Adapter())
        assert Pm5Port in app.adapters

    def test_no_adapter_when_none(self) -> None:
        """When adapter_class is None, no adapter is registered."""
        app = create_app()
        assert Pm5Port not in app.adapters


# =============================================================================
# Payload conversion
# =============================================================================


class TestStatusPayload:
    """_status_payload converts Pm5Status to a JSON-serializable dict.

    Technique: Specification-based Testing — field mapping.
    """

    @pytest.fixture
    def status(self) -> Pm5Status:
        return Pm5Status(
            elapsed_time=125.5,
            distance=500.0,
            pace=120.0,
            speed=2.08,
            stroke_rate=28,
            heart_rate=155,
            calories=42,
            power=180,
            drag_factor=120,
            workout_state=WorkoutState.ACTIVE,
            rowing_state=RowingState.DRIVE,
        )

    def test_all_fields_present(self, status: Pm5Status) -> None:
        payload = _status_payload(status)
        expected_keys = {
            "elapsed_time",
            "distance",
            "pace",
            "speed",
            "stroke_rate",
            "heart_rate",
            "calories",
            "power",
            "drag_factor",
            "workout_state",
            "rowing_state",
        }
        assert set(payload.keys()) == expected_keys

    def test_numeric_values_preserved(self, status: Pm5Status) -> None:
        payload = _status_payload(status)
        assert payload["elapsed_time"] == 125.5
        assert payload["distance"] == 500.0
        assert payload["power"] == 180

    def test_enums_serialized_as_strings(self, status: Pm5Status) -> None:
        payload = _status_payload(status)
        assert payload["workout_state"] == "active"
        assert payload["rowing_state"] == "drive"


class TestStrokePayload:
    """_stroke_payload converts Pm5Stroke to a JSON-serializable dict.

    Technique: Specification-based Testing — field mapping.
    """

    @pytest.fixture
    def stroke(self) -> Pm5Stroke:
        return Pm5Stroke(
            stroke_count=50,
            drive_time=0.85,
            recovery_time=1.15,
            drive_length=1.35,
            stroke_distance=9.8,
            peak_force=450.0,
            average_force=320.0,
            work_per_stroke=285.0,
            stroke_power=190,
            stroke_calories=3.5,
        )

    def test_all_fields_present(self, stroke: Pm5Stroke) -> None:
        payload = _stroke_payload(stroke)
        expected_keys = {
            "stroke_count",
            "drive_time",
            "recovery_time",
            "drive_length",
            "stroke_distance",
            "peak_force",
            "average_force",
            "work_per_stroke",
            "stroke_power",
            "stroke_calories",
        }
        assert set(payload.keys()) == expected_keys

    def test_numeric_values_preserved(self, stroke: Pm5Stroke) -> None:
        payload = _stroke_payload(stroke)
        assert payload["stroke_count"] == 50
        assert payload["peak_force"] == 450.0
        assert payload["stroke_power"] == 190
