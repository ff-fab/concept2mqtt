"""PM5 domain types — the language the Pm5Port speaks.

These frozen dataclasses represent the data that flows through the port
boundary. They map 1:1 to MQTT publishing topics:

- :class:`Pm5Identity`  -> ``pm5/identity/state``
- :class:`Pm5Status`    -> ``pm5/state``
- :class:`Pm5Stroke`    -> ``pm5/stroke/state``
- :class:`Pm5WorkoutSummary` -> ``pm5/workout/state``
- :class:`Pm5ForceCurve` -> ``pm5/force_plot/state``

Values are in human-readable SI units (seconds, metres, watts), not wire
format (centiseconds, decimetres). The translation from csafe-codec raw
types belongs in the adapter, not the domain.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class WorkoutState(StrEnum):
    """High-level workout lifecycle state, derived from csafe-codec's int codes."""

    IDLE = "idle"
    STARTING = "starting"
    ACTIVE = "active"
    PAUSED = "paused"
    FINISHED = "finished"
    UNKNOWN = "unknown"


class RowingState(StrEnum):
    """Per-stroke rowing phase."""

    INACTIVE = "inactive"
    DRIVE = "drive"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Pm5Identity:
    """Static device identity, read once at connection time."""

    serial_number: str
    model: str
    hardware_revision: str
    firmware_revision: str
    manufacturer: str
    erg_type: str


@dataclass(frozen=True, slots=True)
class Pm5Status:
    """Aggregated PM5 state published as ``pm5/state``.

    Combines GeneralStatus and AdditionalStatus1/2 into a single
    domain snapshot. Values are in SI units.
    """

    elapsed_time: float
    """Elapsed workout time in seconds."""

    distance: float
    """Distance covered in metres."""

    pace: float
    """Current pace in seconds per 500 m (0.0 when idle)."""

    speed: float
    """Current speed in metres per second."""

    stroke_rate: int
    """Strokes per minute."""

    heart_rate: int
    """Heart rate in BPM (0 when no belt connected)."""

    calories: int
    """Total calories burned."""

    power: int
    """Current power in watts."""

    drag_factor: int
    """Drag factor (dimensionless)."""

    workout_state: WorkoutState
    rowing_state: RowingState


@dataclass(frozen=True, slots=True)
class Pm5Stroke:
    """Per-stroke metrics published as ``pm5/stroke/state``."""

    stroke_count: int
    drive_time: float
    """Drive phase duration in seconds."""

    recovery_time: float
    """Recovery phase duration in seconds."""

    drive_length: float
    """Drive length in metres."""

    stroke_distance: float
    """Distance per stroke in metres."""

    peak_force: float
    """Peak drive force in Newtons (kg * 10 on wire)."""

    average_force: float
    """Average drive force in Newtons."""

    work_per_stroke: float
    """Work per stroke in joules."""

    stroke_power: int
    """Power for this stroke in watts."""

    stroke_calories: float
    """Calories for this stroke in kcal."""


@dataclass(frozen=True, slots=True)
class Pm5ForceCurve:
    """Force curve data published as ``pm5/force_plot/state``."""

    data_points: Sequence[int]
    """Force values sampled during the drive phase."""

    def __post_init__(self) -> None:
        """Copy mutable caller input before exposing an immutable value object."""
        object.__setattr__(self, "data_points", tuple(self.data_points))


@dataclass(frozen=True, slots=True)
class Pm5WorkoutSummary:
    """End-of-workout summary published as ``pm5/workout/state``."""

    elapsed_time: float
    distance: float
    avg_pace: float
    avg_stroke_rate: int
    avg_heart_rate: int
    avg_drag_factor: int
    workout_type: str


@dataclass(frozen=True, slots=True)
class Pm5SplitInterval:
    """Split or interval data."""

    number: int
    elapsed_time: float
    distance: float
    interval_type: str


# --- Event union ---


@dataclass(frozen=True, slots=True)
class Pm5StatusEvent:
    """A status update from the PM5."""

    status: Pm5Status


@dataclass(frozen=True, slots=True)
class Pm5StrokeEvent:
    """A stroke update from the PM5."""

    stroke: Pm5Stroke


@dataclass(frozen=True, slots=True)
class Pm5ForceCurveEvent:
    """A force curve from the PM5."""

    force_curve: Pm5ForceCurve


@dataclass(frozen=True, slots=True)
class Pm5WorkoutSummaryEvent:
    """Workout has ended — summary available."""

    summary: Pm5WorkoutSummary


@dataclass(frozen=True, slots=True)
class Pm5SplitIntervalEvent:
    """A split or interval boundary was crossed."""

    split: Pm5SplitInterval


type Pm5Event = (
    Pm5StatusEvent
    | Pm5StrokeEvent
    | Pm5ForceCurveEvent
    | Pm5WorkoutSummaryEvent
    | Pm5SplitIntervalEvent
)
"""Union of all events the PM5 can produce."""
