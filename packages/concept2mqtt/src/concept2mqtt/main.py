"""concept2mqtt entrypoint.

Wires the cosalette application with the BleakPm5Adapter and starts
the MQTT bridge. Run via ``uv run concept2mqtt`` or
``python -m concept2mqtt``.
"""

from __future__ import annotations

from concept2mqtt import __version__
from concept2mqtt.app import create_app
from concept2mqtt.pm5.adapter import BleakPm5Adapter


def main() -> None:
    """Start the concept2mqtt CLI with the real BLE adapter."""
    app = create_app(adapter_class=BleakPm5Adapter, version=__version__)
    app.cli()


if __name__ == "__main__":
    main()
