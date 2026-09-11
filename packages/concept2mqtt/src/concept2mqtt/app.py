"""cosalette application scaffold for concept2mqtt.

Creates and configures the cosalette :class:`App` with the PM5 device
handler, adapter registration, and MQTT topic layout. The app is the
composition root — it wires the hexagonal Pm5Port to cosalette's MQTT
publishing infrastructure.

Usage::

    from concept2mqtt.app import create_app
    from concept2mqtt.pm5.fake import FakePm5Adapter

    app = create_app(adapter_class=FakePm5Adapter)
    app.run()
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING

from cosalette import App, DeviceContext

from concept2mqtt.mqtt.topics import APP_NAME, SUB_IDENTITY, SUB_STROKE
from concept2mqtt.pm5.port import Pm5Port
from concept2mqtt.pm5.types import Pm5StatusEvent, Pm5StrokeEvent

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
        5. On shutdown or connection loss, mark unavailable and disconnect.
        """
        pm5 = ctx.adapter(Pm5Port)
        await pm5.connect()
        try:
            ident = await pm5.identity()
            await _publish_identity(ctx, ident)
            await ctx.mark_available()

            async for event in pm5.events():
                match event:
                    case Pm5StatusEvent(status=status):
                        await ctx.publish_state(_status_payload(status))
                    case Pm5StrokeEvent(stroke=stroke):
                        async with ctx.sub_entity(SUB_STROKE) as sub:
                            await sub.publish_state(_stroke_payload(stroke))
            yield
        finally:
            await ctx.mark_unavailable()
            await pm5.disconnect()


async def _publish_identity(ctx: DeviceContext, ident: Pm5Identity) -> None:
    """Publish PM5 identity as a retained sub-entity state."""
    async with ctx.sub_entity(SUB_IDENTITY) as sub:
        await sub.publish_state(
            {
                "serial_number": ident.serial_number,
                "model": ident.model,
                "hardware_revision": ident.hardware_revision,
                "firmware_revision": ident.firmware_revision,
                "manufacturer": ident.manufacturer,
                "erg_type": ident.erg_type,
            },
            retain=True,
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
