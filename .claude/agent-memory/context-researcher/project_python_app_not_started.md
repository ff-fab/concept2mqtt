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
- **`c2m-bm7`** "BLE Adapter — BleakPm5Adapter" (P2) — **all 6 children closed (100%),
  eligible for close but epic issue itself not yet closed as of 2026-09-12**.
  Implemented in commit `1baba69` ("feat: BleakPm5Adapter — real BLE adapter for PM5
  (#24)", merged 2026-09-12): `pm5/adapter.py` (796 LOC) — bleak-based scanning/connect/
  reconnect, GATT identity reads, notification subscription dispatching into csafe-codec
  Rust decoders, wire-to-domain unit conversion (centiseconds→seconds,
  decimetres→metres), multi-characteristic status fusion (GeneralStatus + AS1 + AS2),
  CSAFE request/response with 50 ms inter-frame gap + timeout, notification-rate write
  (1-byte, per the hardware finding in [[project_ble_gateway_architecture]]). 49 unit
  tests in `packages/concept2mqtt/tests/unit/pm5/test_adapter.py` (1271 LOC). A
  follow-up review-remediation child `c2m-kc0` is also closed.
- **`c2m-j2s`** "MVP Integration — Live Telemetry Pipeline" (P2) — **0/4 children
  closed, this is the actual next-up epic**. `app.py`'s `_publish_event` already
  dispatches all `Pm5Event` variants (status/stroke/force_curve/workout_summary/
  split_interval) to MQTT topics per the declared `TOPICS` policy, and `_workout_state`
  in `adapter.py:137` does a raw CSAFE-code→`WorkoutState` enum mapping — but the
  dedicated children are still open:
  - `c2m-j2s.1` workout lifecycle **state machine** (edge/transition detection, not just
    per-notification state mapping) — open, blocks `.2`.
  - `c2m-j2s.2` live telemetry publishing — open, blocked on `.1`.
  - `c2m-j2s.3` health/availability (cosalette health, LWT, retained) — open, not
    apparently started (no health-specific code found outside `ctx.mark_available()` /
    `mark_unavailable()` calls already in `app.py`).
  - `c2m-j2s.4` end-to-end MVP validation on real Pi hardware — open, blocked on `.2`
    and `.3`.

**Known concrete gap (not yet a beads issue as of 2026-09-12):** `main.py` still reads
"Start the CLI without registering an adapter that does not exist yet" and calls
`create_app(version=__version__)` with no `adapter_class` — i.e. `BleakPm5Adapter` is
never wired into the actual CLI entrypoint even though it now exists and is fully
tested. ADR-004's own example code
(`App("concept2mqtt", adapters={Pm5Port: BleakPm5Adapter})`) shows the intended end
state. This wiring is the natural first step of `c2m-j2s` work (or a prerequisite to it)
and should be flagged next time a plan touches this area.

**Also stale:** top-level `README.md` still has templated placeholder content ("Feature
one / Feature two / Feature three", "TODO: Add a minimal usage example").

**Other files:** `pm5/errors.py` (exception hierarchy), `config.py` (pydantic-settings,
currently only `log_level`/`host`/`port` — no PM5-specific or MQTT broker credential
settings yet beyond host/port), `mqtt/topics.py` (`TOPICS` dict, `TopicSpec`, QoS
mapping, `APP_NAME`). Test suite: `packages/concept2mqtt/tests/unit/` mirrors src layout
(`ble/`, `mqtt/`, `pm5/`, plus `test_app.py`, `test_config.py`,
`test_csafe_commands.py`); 364 unit tests all passing as of 2026-09-12
(`task test:unit`).

Cosalette is the application framework declared in `pyproject.toml` (provides `App`,
`DeviceContext`, MQTT publishing, health/LWT primitives).

See also [[project_ble_gateway_architecture]] (separate BLE peripheral-relay track,
`c2m-ooz`, unrelated to this MQTT-publishing app except sharing the BLE hardware
findings) and [[project_csafe_codec_architecture]] (the Rust decoder library this
adapter calls into).
