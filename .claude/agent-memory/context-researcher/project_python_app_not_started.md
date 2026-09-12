---
name: project_python_app_status
description:
  Status of the concept2mqtt Python application (packages/concept2mqtt) — scaffold,
  BleakPm5Adapter, and MQTT publishing wiring; supersedes the old "not started" memory
type: project
---

**Updated 2026-09-12.** This memory previously claimed the app "has no code yet" — that
was already stale by 2026-09-11 and is now doubly so. Filename kept for stable linking;
treat the old title/description as wrong.

**Three epics track the real product**, in dependency order:

- **`c2m-x3b`** "App Scaffold — cosalette + Pm5Port" (P1) — **CLOSED**. Delivered
  `Pm5Port` Protocol + domain types
  (`packages/concept2mqtt/src/concept2mqtt/pm5/port.py`, `types.py`), `FakePm5Adapter`
  (`pm5/fake.py`), cosalette app scaffold (`app.py`), MQTT topic policy
  (`mqtt/topics.py`), and ADR-004
  (`docs/adr/ADR-004-pm5port-hexagonal- architecture-with-cosalette.md`, Accepted
  2026-09-11).
- **`c2m-bm7`** "BLE Adapter — BleakPm5Adapter" (P2) — **CLOSED**. Implemented in commit
  `1baba69` ("feat: BleakPm5Adapter — real BLE adapter for PM5 (#24)", merged
  2026-09-12): `pm5/adapter.py` — bleak-based scanning/connect/ reconnect, GATT identity
  reads, notification subscription dispatching into csafe-codec Rust decoders,
  wire-to-domain unit conversion (centiseconds→seconds, decimetres→metres),
  multi-characteristic status fusion (GeneralStatus + AS1 + AS2), CSAFE request/response
  with 50 ms inter-frame gap + timeout, notification-rate write (1-byte, per the
  hardware finding in [[project_ble_gateway_architecture]]). 49 unit tests in
  `packages/concept2mqtt/tests/unit/pm5/test_adapter.py` (1271 LOC). A follow-up
  review-remediation child `c2m-kc0` is also closed.
- **`c2m-j2s`** "MVP Integration — Live Telemetry Pipeline" (P2) — `c2m-j2s.1` workout
  lifecycle, `c2m-j2s.2` live telemetry publishing, and `c2m-j2s.3` health/availability
  are **CLOSED**. `app.py` dispatches every `Pm5Event` variant
  (status/stroke/force_curve/workout_summary/split_interval) under the declared `TOPICS`
  policy, publishes lifecycle transitions, and marks the device available for its
  connection lifetime. Only **`c2m-j2s.4`**, end-to-end MVP validation on real Pi
  hardware, remains outstanding.

**Production wiring (resolved 2026-09-12):** `main.py` now passes a configured
`BleakPm5Adapter` factory to `create_app`. Startup requires `PM5_ADDRESS` and/or
`PM5_SERIAL_NUMBER`; the adapter connects by configured address when supplied and
rejects a serial-number mismatch before exposing the PM5 connection. Unconfigured,
anonymous discovery remains available only through explicit adapter construction for
development and tests.

**Also stale:** top-level `README.md` still has templated placeholder content ("Feature
one / Feature two / Feature three", "TODO: Add a minimal usage example").

**Other files:** `pm5/errors.py` (exception hierarchy), `config.py` (pydantic-settings,
`log_level`/`host`/`port` plus the `pm5_address` and `pm5_serial_number` production
binding), `mqtt/topics.py` (`TOPICS` dict, `TopicSpec`, QoS mapping, `APP_NAME`). Test
suite: `packages/concept2mqtt/tests/unit/` mirrors src layout (`ble/`, `mqtt/`, `pm5/`,
plus `test_app.py`, `test_config.py`, `test_csafe_commands.py`); 364 unit tests all
passing as of 2026-09-12 (`task test:unit`).

Cosalette is the application framework declared in `pyproject.toml` (provides `App`,
`DeviceContext`, MQTT publishing, health/LWT primitives).

See also [[project_ble_gateway_architecture]] (separate BLE peripheral-relay track,
`c2m-ooz`, unrelated to this MQTT-publishing app except sharing the BLE hardware
findings) and [[project_csafe_codec_architecture]] (the Rust decoder library this
adapter calls into).
