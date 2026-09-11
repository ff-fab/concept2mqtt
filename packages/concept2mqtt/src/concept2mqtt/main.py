"""concept2mqtt entrypoint.

Wires the cosalette application with the configured PM5 adapter and
starts the MQTT bridge. Run via ``uv run concept2mqtt`` or
``python -m concept2mqtt``.
"""

from __future__ import annotations

from concept2mqtt import __version__
from concept2mqtt.app import create_app


def main() -> None:
    """Start the CLI without registering an adapter that does not exist yet."""
    app = create_app(version=__version__)
    app.cli()


if __name__ == "__main__":
    main()
