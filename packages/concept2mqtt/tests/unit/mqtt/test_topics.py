"""Unit tests for concept2mqtt/mqtt/topics.py — MQTT topic layout and QoS mapping.

Test Techniques Used:
- Specification-based Testing: topic path generation, QoS mapping constants
- Equivalence Partitioning: root vs. sub-entity topics
- Decision Table: QoS assignment by topic type (telemetry vs. event)
"""

from __future__ import annotations

import pytest

from concept2mqtt.mqtt.topics import (
    APP_NAME,
    PM5_DEVICE,
    QOS_EVENT,
    QOS_TELEMETRY,
    TOPICS,
    TopicSpec,
    topic_path,
)

# =============================================================================
# Constants
# =============================================================================


class TestConstants:
    """Application and device name constants.

    Technique: Specification-based Testing — constants match the MQTT layout.
    """

    def test_app_name(self) -> None:
        assert APP_NAME == "concept2mqtt"

    def test_pm5_device_name(self) -> None:
        assert PM5_DEVICE == "pm5"

    def test_qos_telemetry_is_zero(self) -> None:
        """High-frequency telemetry uses at-most-once delivery."""
        assert QOS_TELEMETRY == 0

    def test_qos_event_is_one(self) -> None:
        """Events and commands use at-least-once delivery."""
        assert QOS_EVENT == 1


# =============================================================================
# Topic path generation
# =============================================================================


class TestTopicPath:
    """topic_path() builds full MQTT topic strings.

    Technique: Equivalence Partitioning — root device vs. sub-entity.
    """

    def test_root_topic(self) -> None:
        """Root device topic has no sub-entity segment."""
        assert topic_path() == "concept2mqtt/pm5/state"

    @pytest.mark.parametrize(
        ("sub", "expected"),
        [
            ("identity", "concept2mqtt/pm5/identity/state"),
            ("stroke", "concept2mqtt/pm5/stroke/state"),
            ("force_plot", "concept2mqtt/pm5/force_plot/state"),
            ("workout", "concept2mqtt/pm5/workout/state"),
        ],
        ids=["identity", "stroke", "force_plot", "workout"],
    )
    def test_sub_entity_topic(self, sub: str, expected: str) -> None:
        """Sub-entity topics include the entity name."""
        assert topic_path(sub) == expected


# =============================================================================
# QoS mapping
# =============================================================================


class TestQosMapping:
    """TOPICS maps each publishing channel to its QoS.

    Technique: Decision Table — telemetry gets QoS 0, events get QoS 1.
    """

    @pytest.mark.parametrize(
        ("key", "expected_qos"),
        [
            ("state", QOS_TELEMETRY),
            ("stroke", QOS_TELEMETRY),
            ("force_plot", QOS_TELEMETRY),
            ("identity", QOS_EVENT),
            ("workout", QOS_EVENT),
        ],
        ids=["state", "stroke", "force_plot", "identity", "workout"],
    )
    def test_topic_qos(self, key: str, expected_qos: int) -> None:
        assert TOPICS[key].qos == expected_qos

    def test_identity_is_retained(self) -> None:
        """Identity is retained so late subscribers get the current value."""
        assert TOPICS["identity"].retained is True

    def test_telemetry_topics_are_not_retained(self) -> None:
        """Telemetry is transient — only the latest matters."""
        for key in ("state", "stroke", "force_plot"):
            assert TOPICS[key].retained is False, f"{key} should not be retained"


# =============================================================================
# TopicSpec
# =============================================================================


class TestTopicSpec:
    """TopicSpec is a frozen value object.

    Technique: Specification-based Testing.
    """

    def test_topic_spec_frozen(self) -> None:
        spec = TopicSpec(sub_entity="test", qos=0)
        with pytest.raises(AttributeError):
            spec.qos = 1  # type: ignore[misc]  # ty: ignore[invalid-assignment]

    def test_topic_spec_defaults(self) -> None:
        spec = TopicSpec(sub_entity=None, qos=0)
        assert spec.retained is False
