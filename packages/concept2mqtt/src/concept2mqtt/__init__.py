"""concept2mqtt

Connect a concept2 rowing machine's PM5 to MQTT, e.g. for connection to a smart home.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    # Prefer the generated version file (setuptools_scm at build time)
    from ._version import __version__
except ImportError:  # pragma: no cover
    try:
        # Fallback to installed package metadata
        __version__ = version("concept2mqtt")
    except PackageNotFoundError:
        # Last resort fallback for editable installs without metadata
        __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
