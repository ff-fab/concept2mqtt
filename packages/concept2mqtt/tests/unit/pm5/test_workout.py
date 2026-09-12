"""Unit tests for pm5/workout.py -- Workout lifecycle state machine.

Test Techniques Used:
- State Transition Testing: All valid (from, to) state pairs
- Equivalence Partitioning: Transition vs no-transition state changes
- Boundary Value Analysis: Edge cases at state machine boundaries
- Specification-based Testing: WorkoutTransition enum contract
"""

from __future__ import annotations

import pytest

from concept2mqtt.pm5.types import WorkoutState
from concept2mqtt.pm5.workout import WorkoutLifecycle, WorkoutTransition

# =============================================================================
# WorkoutTransition enum
# =============================================================================


class TestWorkoutTransition:
    """WorkoutTransition StrEnum has the expected members.

    Technique: Specification-based Testing -- enum contract.
    """

    def test_started_value(self) -> None:
        assert WorkoutTransition.STARTED == "started"

    def test_paused_value(self) -> None:
        assert WorkoutTransition.PAUSED == "paused"

    def test_resumed_value(self) -> None:
        assert WorkoutTransition.RESUMED == "resumed"

    def test_ended_value(self) -> None:
        assert WorkoutTransition.ENDED == "ended"

    def test_member_count(self) -> None:
        assert len(WorkoutTransition) == 4


# =============================================================================
# WorkoutLifecycle -- initial state
# =============================================================================


class TestWorkoutLifecycleInitialState:
    """WorkoutLifecycle starts in IDLE with no transition on construction.

    Technique: Specification-based Testing -- constructor contract.
    """

    def test_initial_state_is_idle(self) -> None:
        lifecycle = WorkoutLifecycle()
        assert lifecycle.state == WorkoutState.IDLE

    def test_no_transition_on_idle_update(self) -> None:
        # Arrange
        lifecycle = WorkoutLifecycle()

        # Act
        result = lifecycle.update(WorkoutState.IDLE)

        # Assert
        assert result is None


# =============================================================================
# WorkoutLifecycle -- lifecycle transitions
# =============================================================================


class TestWorkoutLifecycleTransitions:
    """Detects lifecycle boundary transitions from WorkoutState changes.

    Technique: State Transition Testing -- all valid (from, to) pairs that
    produce lifecycle events.
    """

    @pytest.fixture
    def lifecycle(self) -> WorkoutLifecycle:
        return WorkoutLifecycle()

    def test_idle_to_active_is_started(self, lifecycle: WorkoutLifecycle) -> None:
        result = lifecycle.update(WorkoutState.ACTIVE)
        assert result == WorkoutTransition.STARTED

    def test_starting_to_active_is_started(self, lifecycle: WorkoutLifecycle) -> None:
        lifecycle.update(WorkoutState.STARTING)
        result = lifecycle.update(WorkoutState.ACTIVE)
        assert result == WorkoutTransition.STARTED

    def test_active_to_paused_is_paused(self, lifecycle: WorkoutLifecycle) -> None:
        lifecycle.update(WorkoutState.ACTIVE)
        result = lifecycle.update(WorkoutState.PAUSED)
        assert result == WorkoutTransition.PAUSED

    def test_paused_to_active_is_resumed(self, lifecycle: WorkoutLifecycle) -> None:
        lifecycle.update(WorkoutState.ACTIVE)
        lifecycle.update(WorkoutState.PAUSED)
        result = lifecycle.update(WorkoutState.ACTIVE)
        assert result == WorkoutTransition.RESUMED

    def test_active_to_finished_is_ended(self, lifecycle: WorkoutLifecycle) -> None:
        lifecycle.update(WorkoutState.ACTIVE)
        result = lifecycle.update(WorkoutState.FINISHED)
        assert result == WorkoutTransition.ENDED

    def test_paused_to_finished_is_ended(self, lifecycle: WorkoutLifecycle) -> None:
        lifecycle.update(WorkoutState.ACTIVE)
        lifecycle.update(WorkoutState.PAUSED)
        result = lifecycle.update(WorkoutState.FINISHED)
        assert result == WorkoutTransition.ENDED


# =============================================================================
# WorkoutLifecycle -- no-op transitions
# =============================================================================


class TestWorkoutLifecycleNoOpTransitions:
    """State changes that are NOT lifecycle boundaries produce None.

    Technique: Equivalence Partitioning -- non-lifecycle state changes.
    """

    @pytest.fixture
    def lifecycle(self) -> WorkoutLifecycle:
        return WorkoutLifecycle()

    def test_same_state_returns_none(self, lifecycle: WorkoutLifecycle) -> None:
        """Repeated identical states produce no transition."""
        lifecycle.update(WorkoutState.ACTIVE)
        result = lifecycle.update(WorkoutState.ACTIVE)
        assert result is None

    def test_idle_to_starting_returns_none(self, lifecycle: WorkoutLifecycle) -> None:
        """Countdown start is not a lifecycle boundary."""
        result = lifecycle.update(WorkoutState.STARTING)
        assert result is None

    def test_finished_to_idle_returns_none(self, lifecycle: WorkoutLifecycle) -> None:
        """Machine reset after workout is not a lifecycle boundary."""
        lifecycle.update(WorkoutState.ACTIVE)
        lifecycle.update(WorkoutState.FINISHED)
        result = lifecycle.update(WorkoutState.IDLE)
        assert result is None

    def test_idle_to_unknown_returns_none(self, lifecycle: WorkoutLifecycle) -> None:
        result = lifecycle.update(WorkoutState.UNKNOWN)
        assert result is None

    def test_unknown_to_idle_returns_none(self, lifecycle: WorkoutLifecycle) -> None:
        lifecycle.update(WorkoutState.UNKNOWN)
        result = lifecycle.update(WorkoutState.IDLE)
        assert result is None

    def test_idle_to_finished_returns_none(self, lifecycle: WorkoutLifecycle) -> None:
        """FINISHED without prior ACTIVE is not a lifecycle boundary."""
        result = lifecycle.update(WorkoutState.FINISHED)
        assert result is None


# =============================================================================
# WorkoutLifecycle -- state tracking
# =============================================================================


class TestWorkoutLifecycleStateTracking:
    """The state property reflects the latest state after each update.

    Technique: State Transition Testing -- state is always current.
    """

    def test_state_updates_on_transition(self) -> None:
        lifecycle = WorkoutLifecycle()
        lifecycle.update(WorkoutState.ACTIVE)
        assert lifecycle.state == WorkoutState.ACTIVE

    def test_state_updates_on_no_op(self) -> None:
        lifecycle = WorkoutLifecycle()
        lifecycle.update(WorkoutState.STARTING)
        assert lifecycle.state == WorkoutState.STARTING


# =============================================================================
# WorkoutLifecycle -- full workout sequence
# =============================================================================


class TestWorkoutLifecycleFullSequence:
    """A complete workout lifecycle produces the correct transition sequence.

    Technique: State Transition Testing -- end-to-end sequence through
    all lifecycle phases.
    """

    def test_full_workout_with_pause(self) -> None:
        """IDLE -> STARTING -> ACTIVE -> PAUSED -> ACTIVE -> FINISHED -> IDLE."""
        lifecycle = WorkoutLifecycle()
        transitions: list[WorkoutTransition] = []

        sequence = [
            WorkoutState.STARTING,
            WorkoutState.ACTIVE,
            WorkoutState.PAUSED,
            WorkoutState.ACTIVE,
            WorkoutState.FINISHED,
            WorkoutState.IDLE,
        ]
        for state in sequence:
            t = lifecycle.update(state)
            if t is not None:
                transitions.append(t)

        assert transitions == [
            WorkoutTransition.STARTED,
            WorkoutTransition.PAUSED,
            WorkoutTransition.RESUMED,
            WorkoutTransition.ENDED,
        ]

    def test_simple_workout_no_pause(self) -> None:
        """IDLE -> ACTIVE -> FINISHED -> IDLE."""
        lifecycle = WorkoutLifecycle()
        transitions: list[WorkoutTransition] = []

        for state in [WorkoutState.ACTIVE, WorkoutState.FINISHED, WorkoutState.IDLE]:
            t = lifecycle.update(state)
            if t is not None:
                transitions.append(t)

        assert transitions == [
            WorkoutTransition.STARTED,
            WorkoutTransition.ENDED,
        ]

    def test_consecutive_workouts(self) -> None:
        """Two back-to-back workouts each produce STARTED and ENDED."""
        lifecycle = WorkoutLifecycle()
        transitions: list[WorkoutTransition] = []

        # First workout
        for state in [WorkoutState.ACTIVE, WorkoutState.FINISHED, WorkoutState.IDLE]:
            t = lifecycle.update(state)
            if t is not None:
                transitions.append(t)

        # Second workout
        for state in [WorkoutState.ACTIVE, WorkoutState.FINISHED, WorkoutState.IDLE]:
            t = lifecycle.update(state)
            if t is not None:
                transitions.append(t)

        assert transitions == [
            WorkoutTransition.STARTED,
            WorkoutTransition.ENDED,
            WorkoutTransition.STARTED,
            WorkoutTransition.ENDED,
        ]

    def test_repeated_status_updates_within_state(self) -> None:
        """Many identical status updates between transitions produce no events."""
        lifecycle = WorkoutLifecycle()

        # 10 idle updates -> no transitions
        for _ in range(10):
            assert lifecycle.update(WorkoutState.IDLE) is None

        # Transition to active
        assert lifecycle.update(WorkoutState.ACTIVE) == WorkoutTransition.STARTED

        # 10 active updates -> no transitions
        for _ in range(10):
            assert lifecycle.update(WorkoutState.ACTIVE) is None

        # End
        assert lifecycle.update(WorkoutState.FINISHED) == WorkoutTransition.ENDED
