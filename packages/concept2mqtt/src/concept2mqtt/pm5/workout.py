"""Workout lifecycle state machine.

Detects workout lifecycle transitions from ``WorkoutState`` changes in
PM5 status notifications. The PM5 broadcasts a workout state code in
every general status notification; this module observes those codes and
emits a :class:`WorkoutTransition` at each lifecycle boundary.

Transition rules::

    (IDLE | STARTING) -> ACTIVE  =>  STARTED
    ACTIVE            -> PAUSED  =>  PAUSED
    PAUSED            -> ACTIVE  =>  RESUMED
    (ACTIVE | PAUSED) -> FINISHED => ENDED

All other state changes (e.g. ``FINISHED -> IDLE``) produce no event.
``UNKNOWN`` is non-authoritative and does not replace the most recent known state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from concept2mqtt.pm5.types import WorkoutState


class WorkoutTransition(StrEnum):
    """Lifecycle boundary events emitted by :class:`WorkoutLifecycle`."""

    STARTED = "started"
    PAUSED = "paused"
    RESUMED = "resumed"
    ENDED = "ended"


# Valid (from_state, to_state) -> transition mappings.
# Only transitions with lifecycle significance are included.
_TRANSITION_TABLE: dict[tuple[WorkoutState, WorkoutState], WorkoutTransition] = {
    (WorkoutState.IDLE, WorkoutState.ACTIVE): WorkoutTransition.STARTED,
    (WorkoutState.STARTING, WorkoutState.ACTIVE): WorkoutTransition.STARTED,
    (WorkoutState.ACTIVE, WorkoutState.PAUSED): WorkoutTransition.PAUSED,
    (WorkoutState.PAUSED, WorkoutState.ACTIVE): WorkoutTransition.RESUMED,
    (WorkoutState.ACTIVE, WorkoutState.FINISHED): WorkoutTransition.ENDED,
    (WorkoutState.PAUSED, WorkoutState.FINISHED): WorkoutTransition.ENDED,
}


@dataclass
class WorkoutLifecycle:
    """Tracks ``WorkoutState`` and emits transitions at lifecycle boundaries.

    Feed every ``Pm5StatusEvent.status.workout_state`` into :meth:`update`.
    When a lifecycle boundary is crossed, the method returns the
    corresponding :class:`WorkoutTransition`; otherwise ``None``.

    Usage::

        lifecycle = WorkoutLifecycle()
        for event in pm5.events():
            if isinstance(event, Pm5StatusEvent):
                transition = lifecycle.update(event.status.workout_state)
                if transition is not None:
                    publish_lifecycle_event(transition)
    """

    _state: WorkoutState = field(default=WorkoutState.IDLE, init=False)

    @property
    def state(self) -> WorkoutState:
        """The current workout state."""
        return self._state

    def update(self, new_state: WorkoutState) -> WorkoutTransition | None:
        """Process a new workout state, returning a transition if one occurred.

        Args:
            new_state: The latest ``WorkoutState`` from a status notification.

        Returns:
            The lifecycle transition, or ``None`` if no boundary was crossed.
        """
        if new_state is WorkoutState.UNKNOWN:
            return None
        if new_state == self._state:
            return None
        transition = _TRANSITION_TABLE.get((self._state, new_state))
        self._state = new_state
        return transition
