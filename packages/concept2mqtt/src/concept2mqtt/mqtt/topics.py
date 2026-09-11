"""MQTT topic layout and QoS mapping for the PM5 device.

Topic structure (under cosalette's ``{topic_prefix}/{device_name}/`` root):

    concept2mqtt/pm5/state              — aggregated PM5 status (QoS 0)
    concept2mqtt/pm5/availability       — online/offline (managed by cosalette)
    concept2mqtt/pm5/identity/state     — static device identity (QoS 1, retained)
    concept2mqtt/pm5/workout/state      — workout lifecycle events (QoS 1)
    concept2mqtt/pm5/stroke/state       — per-stroke metrics (QoS 0)
    concept2mqtt/pm5/force_plot/state   — force curve data (QoS 0)
    concept2mqtt/pm5/set                — inbound commands (QoS 1)
    concept2mqtt/pm5/error              — error reports (managed by cosalette)

QoS policy:
- QoS 0 (at-most-once) for high-frequency telemetry — one missed stroke
  update is not actionable; the next one arrives within ~2 s.
- QoS 1 (at-least-once) for events and commands — workout start/end and
  identity must not be silently lost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# ---------------------------------------------------------------------------
# Application and device names
# ---------------------------------------------------------------------------

APP_NAME: Final = "concept2mqtt"
"""cosalette application name — root of all topic paths."""

PM5_DEVICE: Final = "pm5"
"""cosalette device name for the PM5 rowing monitor."""

# ---------------------------------------------------------------------------
# Sub-entity names (cosalette sub_entity("name") → pm5/{name}/state)
# ---------------------------------------------------------------------------

SUB_IDENTITY: Final = "identity"
SUB_WORKOUT: Final = "workout"
SUB_STROKE: Final = "stroke"
SUB_FORCE_PLOT: Final = "force_plot"

# ---------------------------------------------------------------------------
# QoS mapping
# ---------------------------------------------------------------------------

QOS_TELEMETRY: Final = 0
"""High-frequency data: status, stroke metrics, force curves."""

QOS_EVENT: Final = 1
"""Low-frequency events and commands: identity, workout lifecycle, set."""


@dataclass(frozen=True, slots=True)
class TopicSpec:
    """A topic's sub-entity name (or None for the root) and its QoS."""

    sub_entity: str | None
    qos: int
    retained: bool = False


# All topic specs for the PM5 device
TOPICS: Final[dict[str, TopicSpec]] = {
    "state": TopicSpec(sub_entity=None, qos=QOS_TELEMETRY),
    "identity": TopicSpec(sub_entity=SUB_IDENTITY, qos=QOS_EVENT, retained=True),
    "workout": TopicSpec(sub_entity=SUB_WORKOUT, qos=QOS_EVENT),
    "stroke": TopicSpec(sub_entity=SUB_STROKE, qos=QOS_TELEMETRY),
    "force_plot": TopicSpec(sub_entity=SUB_FORCE_PLOT, qos=QOS_TELEMETRY),
}


def topic_path(sub_entity: str | None = None) -> str:
    """Build a full MQTT topic path for debugging and logging.

    Example::

        >>> topic_path()
        'concept2mqtt/pm5/state'
        >>> topic_path("stroke")
        'concept2mqtt/pm5/stroke/state'
    """
    if sub_entity:
        return f"{APP_NAME}/{PM5_DEVICE}/{sub_entity}/state"
    return f"{APP_NAME}/{PM5_DEVICE}/state"
