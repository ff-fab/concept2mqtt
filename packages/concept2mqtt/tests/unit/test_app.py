"""Unit tests for concept2mqtt/app.py — cosalette application scaffold.

Test Techniques Used:
- Specification-based Testing: create_app factory, adapter registration,
  payload conversion
- Equivalence Partitioning: with/without adapter class
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import suppress
from typing import cast

import pytest
from cosalette import DeviceContext
from cosalette.testing import AppHarness

from concept2mqtt.app import _status_payload, _stroke_payload, create_app
from concept2mqtt.mqtt.topics import APP_NAME
from concept2mqtt.pm5.fake import FakePm5Adapter
from concept2mqtt.pm5.port import Pm5Port
from concept2mqtt.pm5.types import (
    Pm5Event,
    Pm5ForceCurve,
    Pm5ForceCurveEvent,
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
        """A PM5 device handler is registered only with a concrete adapter."""
        app = create_app(adapter_class=lambda: FakePm5Adapter())
        assert "pm5" in app.registered_names

    def test_adapter_registered_via_factory(self) -> None:
        """When a factory callable is provided, it's registered for Pm5Port.

        FakePm5Adapter has generic type annotations in __init__ that
        cosalette's DI cannot introspect, so we register a zero-arg factory.
        """
        app = create_app(adapter_class=lambda: FakePm5Adapter())
        assert Pm5Port in app.adapters

    def test_no_adapter_when_none(self) -> None:
        """Without a production adapter, no unresolved PM5 device is registered."""
        app = create_app()
        assert Pm5Port not in app.adapters
        assert "pm5" not in app.registered_names


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


class TestPm5DeviceHandler:
    """The device handler yields promptly and honours every topic policy."""

    async def test_yields_after_setup_and_publishes_live_stroke(self) -> None:
        adapter = FakePm5Adapter()
        app = create_app(adapter_class=lambda: adapter)
        harness = AppHarness.create(name=APP_NAME)
        ctx = DeviceContext(
            name="pm5",
            settings=harness.settings,
            mqtt=harness.mqtt,
            topic_prefix=APP_NAME,
            shutdown_event=harness.shutdown_event,
            adapters={Pm5Port: adapter},
            clock=harness.clock,
        )
        handler = cast(AsyncGenerator[None], app._devices[0].func(ctx))

        await anext(handler)
        assert adapter.connected
        assert harness.messages_for("concept2mqtt/pm5/identity/state")[0][2] == 1

        stroke = Pm5Stroke(1, 0.8, 1.2, 1.3, 9.0, 400.0, 300.0, 250.0, 180, 3.0)
        adapter.emit(Pm5StrokeEvent(stroke))
        await anext(handler)

        payload, retained, qos = harness.messages_for("concept2mqtt/pm5/stroke/state")[
            -1
        ]
        assert '"stroke_count":1' in payload
        assert not retained
        assert qos == 0
        await handler.aclose()
        assert adapter.disconnect_count == 1

    @pytest.mark.parametrize(
        ("event", "topic", "expected_qos"),
        [
            (
                Pm5StatusEvent(
                    Pm5Status(
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        WorkoutState.IDLE,
                        RowingState.INACTIVE,
                    )
                ),
                "concept2mqtt/pm5/state",
                0,
            ),
            (
                Pm5ForceCurveEvent(Pm5ForceCurve((1, 2))),
                "concept2mqtt/pm5/force_plot/state",
                0,
            ),
            (
                Pm5WorkoutSummaryEvent(Pm5WorkoutSummary(1, 2, 3, 4, 5, 6, "just_row")),
                "concept2mqtt/pm5/workout/state",
                1,
            ),
            (
                Pm5SplitIntervalEvent(Pm5SplitInterval(1, 2, 3, "work")),
                "concept2mqtt/pm5/workout/state",
                1,
            ),
        ],
    )
    async def test_publishes_every_declared_event_variant(
        self, event: Pm5Event, topic: str, expected_qos: int
    ) -> None:
        adapter = FakePm5Adapter()
        app = create_app(adapter_class=lambda: adapter)
        harness = AppHarness.create(name=APP_NAME)
        ctx = DeviceContext(
            name="pm5",
            settings=harness.settings,
            mqtt=harness.mqtt,
            topic_prefix=APP_NAME,
            shutdown_event=harness.shutdown_event,
            adapters={Pm5Port: adapter},
            clock=harness.clock,
        )
        handler = cast(AsyncGenerator[None], app._devices[0].func(ctx))
        await anext(handler)
        adapter.emit(event)
        await anext(handler)

        _payload, retained, qos = harness.messages_for(topic)[-1]
        assert not retained
        assert qos == expected_qos
        with suppress(StopAsyncIteration):
            await handler.aclose()

    async def test_publishes_lifecycle_transition_on_workout_start(self) -> None:
        """Status event with ACTIVE workout state publishes a lifecycle event."""
        adapter = FakePm5Adapter()
        app = create_app(adapter_class=lambda: adapter)
        harness = AppHarness.create(name=APP_NAME)
        ctx = DeviceContext(
            name="pm5",
            settings=harness.settings,
            mqtt=harness.mqtt,
            topic_prefix=APP_NAME,
            shutdown_event=harness.shutdown_event,
            adapters={Pm5Port: adapter},
            clock=harness.clock,
        )
        handler = cast(AsyncGenerator[None], app._devices[0].func(ctx))
        await anext(handler)

        # Emit a status event with ACTIVE workout state (transition from IDLE)
        active_status = Pm5Status(
            10.0,
            50.0,
            120.0,
            2.0,
            28,
            0,
            5,
            180,
            120,
            WorkoutState.ACTIVE,
            RowingState.DRIVE,
        )
        adapter.emit(Pm5StatusEvent(active_status))
        await anext(handler)

        # Should have published both the status AND a lifecycle event
        workout_msgs = harness.messages_for("concept2mqtt/pm5/workout/state")
        assert len(workout_msgs) >= 1
        lifecycle_payload = workout_msgs[-1][0]
        assert '"event":"started"' in lifecycle_payload
        assert workout_msgs[-1][2] == 1  # QoS 1

        with suppress(StopAsyncIteration):
            await handler.aclose()

    async def test_no_lifecycle_event_for_same_workout_state(self) -> None:
        """Repeated same-state status events produce no lifecycle event."""
        adapter = FakePm5Adapter()
        app = create_app(adapter_class=lambda: adapter)
        harness = AppHarness.create(name=APP_NAME)
        ctx = DeviceContext(
            name="pm5",
            settings=harness.settings,
            mqtt=harness.mqtt,
            topic_prefix=APP_NAME,
            shutdown_event=harness.shutdown_event,
            adapters={Pm5Port: adapter},
            clock=harness.clock,
        )
        handler = cast(AsyncGenerator[None], app._devices[0].func(ctx))
        await anext(handler)

        # Two IDLE status events -- no lifecycle transition expected
        idle_status = Pm5Status(
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            WorkoutState.IDLE,
            RowingState.INACTIVE,
        )
        adapter.emit(Pm5StatusEvent(idle_status))
        await anext(handler)
        adapter.emit(Pm5StatusEvent(idle_status))
        await anext(handler)

        workout_msgs = harness.messages_for("concept2mqtt/pm5/workout/state")
        assert len(workout_msgs) == 0

        with suppress(StopAsyncIteration):
            await handler.aclose()
