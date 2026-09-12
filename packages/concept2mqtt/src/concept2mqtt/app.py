"""cosalette application scaffold for concept2mqtt.

Creates and configures the cosalette :class:`App` with the PM5 device
handler, adapter registration, and MQTT topic layout. The app is the
composition root — it wires the hexagonal Pm5Port to cosalette's MQTT
publishing infrastructure.

Usage::

    from concept2mqtt.app import create_app
    from concept2mqtt.pm5.fake import FakePm5Adapter

    app = create_app(adapter_class=lambda: FakePm5Adapter())
    app.run()
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING

from cosalette import App, DeviceContext

from concept2mqtt.mqtt.topics import APP_NAME, TOPICS, TopicSpec
from concept2mqtt.pm5.port import Pm5Port
from concept2mqtt.pm5.types import (
    Pm5ForceCurveEvent,
    Pm5SplitIntervalEvent,
    Pm5StatusEvent,
    Pm5StrokeEvent,
    Pm5WorkoutSummaryEvent,
)
from concept2mqtt.pm5.workout import WorkoutLifecycle

if TYPE_CHECKING:
    from concept2mqtt.pm5.types import Pm5Identity, Pm5Status, Pm5Stroke


def create_app(
    *,
    adapter_class: type | Callable[..., object] | None = None,
    version: str = "0.0.0",
) -> App:
    """Build the cosalette application.

    Args:
        adapter_class: Pm5Port implementation to register. Can be a class
            or a zero-arg factory callable. When ``None``, no adapter is
            registered (useful for dry-run or documentation).
        version: Application version string (injected by packaging).
    """
    adapters: (
        dict[
            type,
            type
            | str
            | Callable[..., object]
            | tuple[
                type | str | Callable[..., object],
                type | str | Callable[..., object],
            ],
        ]
        | None
    ) = None
    if adapter_class is not None:
        adapters = {Pm5Port: adapter_class}

    app = App(
        APP_NAME,
        version=version,
        description="Concept2 PM5 rowing monitor to MQTT bridge",
        adapters=adapters,
    )

    # A PM5 device cannot run without a concrete port implementation.  The
    # production BLE adapter is intentionally not scaffolded as a fake.
    if adapter_class is not None:
        _register_pm5_device(app)
    return app


def _register_pm5_device(app: App) -> None:
    """Register the pm5 device handler on the app."""

    @app.device("pm5")
    async def pm5_device(ctx: DeviceContext) -> AsyncIterator[None]:
        """PM5 device handler — reads identity, streams telemetry to MQTT.

        Lifecycle:
        1. Connect to the PM5 via the injected adapter.
        2. Read and publish identity (retained, QoS 1).
        3. Mark the device as available.
        4. Stream events, publishing each to the appropriate sub-entity.
           Workout lifecycle transitions (started/paused/resumed/ended)
           are detected and published to the workout topic.
        5. On shutdown or connection loss, mark unavailable and disconnect.
        """
        pm5 = ctx.adapter(Pm5Port)
        lifecycle = WorkoutLifecycle()
        await pm5.connect()
        try:
            ident = await pm5.identity()
            await _publish_identity(ctx, ident)
            await ctx.mark_available()

            # Yield once setup is complete so cosalette can finish startup.
            # Every subsequent event is also a reactor boundary.  Keeping the
            # sub-entities open for the connection lifetime avoids emitting an
            # availability transition for every stroke.
            async with _pm5_sub_entities(ctx):
                yield
                async for event in pm5.events():
                    await _publish_event(ctx, event)
                    if isinstance(event, Pm5StatusEvent):
                        await _publish_lifecycle(ctx, lifecycle, event)
                    yield
        finally:
            await ctx.mark_unavailable()
            await pm5.disconnect()


async def _publish_identity(ctx: DeviceContext, ident: Pm5Identity) -> None:
    """Publish PM5 identity as a retained sub-entity state."""
    await _publish_topic(
        ctx,
        "identity",
        {
            "serial_number": ident.serial_number,
            "model": ident.model,
            "hardware_revision": ident.hardware_revision,
            "firmware_revision": ident.firmware_revision,
            "manufacturer": ident.manufacturer,
            "erg_type": ident.erg_type,
        },
    )


async def _publish_lifecycle(
    ctx: DeviceContext,
    lifecycle: WorkoutLifecycle,
    event: Pm5StatusEvent,
) -> None:
    """Detect and publish workout lifecycle transitions."""
    transition = lifecycle.update(event.status.workout_state)
    if transition is not None:
        await _publish_topic(ctx, "workout", {"event": transition.value})


@asynccontextmanager
async def _pm5_sub_entities(ctx: DeviceContext) -> AsyncIterator[None]:
    """Keep PM5 sub-entities available for one connected device session."""
    async with AsyncExitStack() as stack:
        for key in ("identity", "workout", "stroke", "force_plot"):
            await stack.enter_async_context(
                ctx.sub_entity(_topic(key).sub_entity or "")
            )
        yield


async def _publish_event(ctx: DeviceContext, event: object) -> None:
    """Publish every event variant defined by :class:`Pm5Event`."""
    match event:
        case Pm5StatusEvent(status=status):
            await _publish_topic(ctx, "state", _status_payload(status))
        case Pm5StrokeEvent(stroke=stroke):
            await _publish_topic(ctx, "stroke", _stroke_payload(stroke))
        case Pm5ForceCurveEvent(force_curve=force_curve):
            await _publish_topic(
                ctx, "force_plot", {"data_points": force_curve.data_points}
            )
        case Pm5WorkoutSummaryEvent(summary=summary):
            await _publish_topic(
                ctx,
                "workout",
                {
                    "event": "summary",
                    "elapsed_time": summary.elapsed_time,
                    "distance": summary.distance,
                    "avg_pace": summary.avg_pace,
                    "avg_stroke_rate": summary.avg_stroke_rate,
                    "avg_heart_rate": summary.avg_heart_rate,
                    "avg_drag_factor": summary.avg_drag_factor,
                    "workout_type": summary.workout_type,
                },
            )
        case Pm5SplitIntervalEvent(split=split):
            await _publish_topic(
                ctx,
                "workout",
                {
                    "event": "split_interval",
                    "number": split.number,
                    "elapsed_time": split.elapsed_time,
                    "distance": split.distance,
                    "interval_type": split.interval_type,
                },
            )
        case _:
            msg = f"Unsupported PM5 event: {type(event).__name__}"
            raise TypeError(msg)


def _topic(key: str) -> TopicSpec:
    """Return a declared PM5 topic, failing loudly on a programming error."""
    return TOPICS[key]


async def _publish_topic(
    ctx: DeviceContext, key: str, payload: dict[str, object]
) -> None:
    """Publish according to the single, declared :data:`TOPICS` policy."""
    spec = _topic(key)
    channel = "state" if spec.sub_entity is None else f"{spec.sub_entity}/state"
    await ctx.publish(
        channel,
        json.dumps(payload, separators=(",", ":")),
        retain=spec.retained,
        qos=spec.qos,
    )


def _status_payload(status: Pm5Status) -> dict[str, object]:
    """Convert Pm5Status to a dict for MQTT publishing."""
    return {
        "elapsed_time": status.elapsed_time,
        "distance": status.distance,
        "pace": status.pace,
        "speed": status.speed,
        "stroke_rate": status.stroke_rate,
        "heart_rate": status.heart_rate,
        "calories": status.calories,
        "power": status.power,
        "drag_factor": status.drag_factor,
        "workout_state": status.workout_state.value,
        "rowing_state": status.rowing_state.value,
    }


def _stroke_payload(stroke: Pm5Stroke) -> dict[str, object]:
    """Convert Pm5Stroke to a dict for MQTT publishing."""
    return {
        "stroke_count": stroke.stroke_count,
        "drive_time": stroke.drive_time,
        "recovery_time": stroke.recovery_time,
        "drive_length": stroke.drive_length,
        "stroke_distance": stroke.stroke_distance,
        "peak_force": stroke.peak_force,
        "average_force": stroke.average_force,
        "work_per_stroke": stroke.work_per_stroke,
        "stroke_power": stroke.stroke_power,
        "stroke_calories": stroke.stroke_calories,
    }
