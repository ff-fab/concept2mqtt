"""concept2mqtt entrypoint.

Wires the cosalette application with the BleakPm5Adapter and starts
the MQTT bridge. Run via ``uv run concept2mqtt`` or
``python -m concept2mqtt``.
"""

from __future__ import annotations

from functools import partial

from concept2mqtt import __version__
from concept2mqtt.app import create_app
from concept2mqtt.config import get_settings
from concept2mqtt.pm5.adapter import BleakPm5Adapter


def main() -> None:
    """Start the concept2mqtt CLI with the real BLE adapter."""
    adapter_factory = partial(BleakPm5Adapter, **get_settings().pm5_adapter_kwargs())
    app = create_app(adapter_class=adapter_factory, version=__version__)
    app.cli()


if __name__ == "__main__":
    main()
