"""Unit tests for concept2mqtt/pm5/types.py — PM5 domain types.

Test Techniques Used:
- Specification-based Testing: frozen dataclass contracts, enum membership
- Error Guessing: mutation of frozen instances
- Equivalence Partitioning: WorkoutState and RowingState enum values
"""

from __future__ import annotations

import pytest

from concept2mqtt.pm5.types import (
    Pm5ForceCurve,
    Pm5ForceCurveEvent,
    Pm5Identity,
    Pm5SplitInterval,
    Pm5SplitIntervalEvent,
    Pm5Status,
    Pm5StatusEvent,
    Pm5Stroke,
    Pm5StrokeEvent,
    Pm5WorkoutSummary,
    Pm5WorkoutSummaryEvent,
    RowingState,
    WorkoutState,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def identity() -> Pm5Identity:
    """Sample PM5 identity."""
    return Pm5Identity(
        serial_number="530426599",
        model="PM5",
        hardware_revision="672",
        firmware_revision="2.10",
        manufacturer="Concept2",
        erg_type="RowErg",
    )


@pytest.fixture
def status() -> Pm5Status:
    """Sample mid-workout status."""
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


@pytest.fixture
def stroke() -> Pm5Stroke:
    """Sample stroke data."""
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


# =============================================================================
# Enums
# =============================================================================


class TestWorkoutState:
    """WorkoutState covers the PM5 workout lifecycle.

    Technique: Equivalence Partitioning — each state is a distinct partition.
    """

    @pytest.mark.parametrize(
        "state",
        list(WorkoutState),
        ids=[s.name for s in WorkoutState],
    )
    def test_workout_state_is_a_string(self, state: WorkoutState) -> None:
        """Every WorkoutState value is a plain string for JSON serialization."""
        assert isinstance(state, str)

    def test_workout_state_has_expected_members(self) -> None:
        """All lifecycle states are represented."""
        expected = {"idle", "starting", "active", "paused", "finished", "unknown"}
        assert {s.value for s in WorkoutState} == expected


class TestRowingState:
    """RowingState covers the per-stroke phase.

    Technique: Equivalence Partitioning.
    """

    def test_rowing_state_has_expected_members(self) -> None:
        expected = {"inactive", "drive", "recovery", "unknown"}
        assert {s.value for s in RowingState} == expected


# =============================================================================
# Frozen dataclasses
# =============================================================================


class TestPm5Identity:
    """Pm5Identity is a frozen value object.

    Technique: Specification-based Testing — constructor contract, immutability.
    """

    def test_identity_fields_are_accessible(self, identity: Pm5Identity) -> None:
        """All identity fields are readable."""
        assert identity.serial_number == "530426599"
        assert identity.model == "PM5"
        assert identity.manufacturer == "Concept2"
        assert identity.erg_type == "RowErg"

    def test_identity_is_frozen(self, identity: Pm5Identity) -> None:
        """Mutation raises FrozenInstanceError.

        Technique: Error Guessing — anticipating mutation attempt.
        """
        with pytest.raises(AttributeError):
            identity.serial_number = "000000000"  # type: ignore[misc]  # ty: ignore[invalid-assignment]

    def test_identity_equality(self) -> None:
        """Two identities with the same fields are equal."""
        a = Pm5Identity("1", "PM5", "1", "1", "C2", "Row")
        b = Pm5Identity("1", "PM5", "1", "1", "C2", "Row")
        assert a == b


class TestPm5Status:
    """Pm5Status aggregates real-time workout state.

    Technique: Specification-based Testing — field access and types.
    """

    def test_status_fields_use_si_units(self, status: Pm5Status) -> None:
        """Time in seconds, distance in metres, speed in m/s."""
        assert status.elapsed_time == 125.5
        assert status.distance == 500.0
        assert status.speed == 2.08

    def test_status_workout_state_is_enum(self, status: Pm5Status) -> None:
        assert status.workout_state is WorkoutState.ACTIVE
        assert status.rowing_state is RowingState.DRIVE

    def test_status_is_frozen(self, status: Pm5Status) -> None:
        with pytest.raises(AttributeError):
            status.distance = 999.0  # type: ignore[misc]  # ty: ignore[invalid-assignment]


class TestPm5Stroke:
    """Pm5Stroke captures per-stroke metrics.

    Technique: Specification-based Testing.
    """

    def test_stroke_fields(self, stroke: Pm5Stroke) -> None:
        assert stroke.stroke_count == 50
        assert stroke.drive_time == 0.85
        assert stroke.peak_force == 450.0
        assert stroke.stroke_power == 190

    def test_stroke_is_frozen(self, stroke: Pm5Stroke) -> None:
        with pytest.raises(AttributeError):
            stroke.stroke_count = 99  # type: ignore[misc]  # ty: ignore[invalid-assignment]


class TestPm5ForceCurve:
    """Pm5ForceCurve wraps the force-plot sample array.

    Technique: Specification-based Testing.
    """

    def test_force_curve_data_points(self) -> None:
        fc = Pm5ForceCurve(data_points=[100, 200, 300, 250, 150])
        assert len(fc.data_points) == 5
        assert fc.data_points[2] == 300


class TestPm5WorkoutSummary:
    """Pm5WorkoutSummary represents end-of-workout data.

    Technique: Specification-based Testing.
    """

    def test_summary_fields(self) -> None:
        summary = Pm5WorkoutSummary(
            elapsed_time=1200.0,
            distance=5000.0,
            avg_pace=120.0,
            avg_stroke_rate=28,
            avg_heart_rate=160,
            avg_drag_factor=120,
            workout_type="JustRowNoSplits",
        )
        assert summary.distance == 5000.0
        assert summary.avg_stroke_rate == 28


class TestPm5SplitInterval:
    """Pm5SplitInterval represents a split or interval boundary.

    Technique: Specification-based Testing.
    """

    def test_split_fields(self) -> None:
        split = Pm5SplitInterval(
            number=1,
            elapsed_time=240.0,
            distance=1000.0,
            interval_type="Distance",
        )
        assert split.number == 1
        assert split.distance == 1000.0


# =============================================================================
# Event wrappers
# =============================================================================


class TestEventTypes:
    """Event wrappers carry domain data for the Pm5Port event stream.

    Technique: Specification-based Testing — wrapper contract.
    """

    def test_status_event_wraps_status(self, status: Pm5Status) -> None:
        event = Pm5StatusEvent(status=status)
        assert event.status is status

    def test_stroke_event_wraps_stroke(self, stroke: Pm5Stroke) -> None:
        event = Pm5StrokeEvent(stroke=stroke)
        assert event.stroke is stroke

    def test_force_curve_event(self) -> None:
        fc = Pm5ForceCurve(data_points=[1, 2, 3])
        event = Pm5ForceCurveEvent(force_curve=fc)
        assert event.force_curve.data_points == [1, 2, 3]

    def test_workout_summary_event(self) -> None:
        summary = Pm5WorkoutSummary(
            elapsed_time=600.0,
            distance=2500.0,
            avg_pace=120.0,
            avg_stroke_rate=26,
            avg_heart_rate=150,
            avg_drag_factor=115,
            workout_type="FixedDistanceNoSplits",
        )
        event = Pm5WorkoutSummaryEvent(summary=summary)
        assert event.summary.workout_type == "FixedDistanceNoSplits"

    def test_split_interval_event(self) -> None:
        split = Pm5SplitInterval(
            number=2,
            elapsed_time=480.0,
            distance=2000.0,
            interval_type="Time",
        )
        event = Pm5SplitIntervalEvent(split=split)
        assert event.split.number == 2
