"""Unit tests for concept2mqtt/main.py -- CLI composition root.

Test Techniques Used:
- Specification-based Testing: production adapter DI and CLI invocation
- Decision Table Testing: configured and missing PM5 identity inputs
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

import concept2mqtt.main as main_module
from concept2mqtt.config import Settings
from concept2mqtt.pm5.adapter import BleakPm5Adapter


class TestMain:
    """main() creates a trusted production adapter before running the CLI.

    Technique: Specification-based Testing -- composition-root contract.
    """

    def test_main_wires_configured_production_adapter_and_invokes_cli(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        settings = Settings(
            pm5_address="AA:BB:CC:DD:EE:FF", pm5_serial_number="530426599"
        )
        app = Mock()
        create_app = Mock(return_value=app)
        monkeypatch.setattr(main_module, "get_settings", lambda: settings)
        monkeypatch.setattr(main_module, "create_app", create_app)

        main_module.main()

        adapter_factory = create_app.call_args.kwargs["adapter_class"]
        adapter = adapter_factory()
        assert isinstance(adapter, BleakPm5Adapter)
        assert adapter.address == "AA:BB:CC:DD:EE:FF"
        assert adapter.expected_serial_number == "530426599"
        assert create_app.call_args.kwargs["version"] == main_module.__version__
        app.cli.assert_called_once_with()

    def test_main_fails_before_creating_app_without_pm5_binding(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        create_app = Mock()
        monkeypatch.setattr(main_module, "get_settings", Settings)
        monkeypatch.setattr(main_module, "create_app", create_app)

        with pytest.raises(ValueError, match="PM5_ADDRESS"):
            main_module.main()

        create_app.assert_not_called()
