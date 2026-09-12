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
binding), `mqtt/topics.py` (`TOPICS` dict, `TopicSpec`, QoS mapping, `APP_NAME`),
`pm5/workout.py` (88 LOC, workout lifecycle state machine landed in #25). Test suite:
`packages/concept2mqtt/tests/unit/` mirrors src layout (`ble/`, `mqtt/`, `pm5/`, plus
`test_app.py`, `test_config.py`, `test_csafe_commands.py`, `test_main.py`); 401 unit
tests all passing as of 2026-09-12 later same day (`task c2m:test`), no
`tests/integration/` dir exists yet for concept2mqtt (Taskfile guards for this and skips
gracefully). No TODO/FIXME/NotImplementedError markers in `packages/concept2mqtt/src` or
`packages/csafe-codec/src`.

**CI note (2026-09-12):** the Release Please workflow run on `main` after #25 merged
failed with
`release-please failed: GitHub Actions is not permitted to create or approve pull requests`
— a repo Actions-permissions setting issue, not a code defect. Also logged a harmless
parse warning on the `Merge pull request #23 from ...` commit message (not
conventional-commits format, expected for merge commits, ignored by release-please
otherwise). Root `pyproject.toml`: `requires-python = ">=3.14"`, key deps
`bleak>=0.22.0`, `cosalette>=0.9.6`.

Cosalette is the application framework declared in `pyproject.toml` (provides `App`,
`DeviceContext`, MQTT publishing, health/LWT primitives).

**Runtime configuration is split across two separate `Settings` classes — easy to
miss:**

- `concept2mqtt.config.Settings` (`packages/concept2mqtt/src/concept2mqtt/config.py`) —
  only `log_level`, `host`/`port` (labelled "network service settings" but not actually
  wired to anything read in `app.py`), and the PM5 binding: `PM5_ADDRESS`,
  `PM5_SERIAL_NUMBER` (at least one required, enforced by `pm5_adapter_kwargs()`, else
  `main()` raises before `create_app`). Loads from `.env` via pydantic-settings.
- Cosalette's own `Settings`
  (`.venv/lib/python3.14/site-packages/cosalette/_settings/__init__.py`, read inside
  `App.cli()` via `--env-file`/`--config-file`, default `.env`) owns the **MQTT broker
  connection**, nested under `MQTT__*`: `MQTT__HOST` (default `localhost`), `MQTT__PORT`
  (default `1883`), `MQTT__USERNAME`/`MQTT__PASSWORD` (optional), `MQTT__TLS` (**default
  `True`** — local/dev brokers without TLS need explicit `MQTT__TLS=false`),
  `MQTT__TLS_CA_FILE`/`_CERT_FILE`/`_KEY_FILE`, `MQTT__CLIENT_ID` (default `""` →
  auto-generated `{name}-{hex8}`), `MQTT__RECONNECT_INTERVAL` (5.0),
  `MQTT__RECONNECT_MAX_INTERVAL` (300.0), `MQTT__TOPIC_PREFIX`,
  `MQTT__ERROR_PUBLISH_VERBOSE` (default `False`), `MQTT__MAX_INBOUND_PAYLOAD_BYTES`
  (262144). Also `LOGGING__*` and `SCHEMA__*` nested groups.
- No env var exists yet for **BLE adapter selection** in the production app path —
  `BleakPm5Adapter.adapter: str | None = None` (`pm5/adapter.py:263`) accepts an hciN
  name, but `main.py` never passes it (only `pm5_adapter_kwargs()`), so it always uses
  bleak's default adapter. This only matters for concept2mqtt's own single central
  connection — the _relay's_ second adapter (`hci1`) is a
  `docs/planning/legacy/examples/relay_pm5.py` `--peripheral` CLI flag, not an env var,
  and is unrelated to this Settings class.
- Root `README.md` and repo have **no `.env.example`** — only a real (gitignored) `.env`
  in the repo root, which holds unrelated CI/tooling secrets (`GH_TOKEN`,
  `CONTEXT7_API_KEY`), not PM5/MQTT config. Do not treat it as a template.
- No Taskfile task exists for running/deploying the app on a Pi (checked root
  `Taskfile.yml` in full — only test/lint/docs/beads/PR/CI tasks; no `task run` /
  `task deploy` / `task c2m:run`). Running on hardware today means `uv run concept2mqtt`
  or `python -m concept2mqtt` directly on the Pi with `.env` populated. There is also no
  `packages/concept2mqtt/Taskfile.yml` — all `c2m:*` aliases live in the root Taskfile
  and just parametrize the generic `test:*`/`lint`/`typecheck` tasks with
  `PKG=packages/concept2mqtt`.

See also [[project_ble_gateway_architecture]] (separate BLE peripheral-relay track,
`c2m-ooz`, unrelated to this MQTT-publishing app except sharing the BLE hardware
findings) and [[project_csafe_codec_architecture]] (the Rust decoder library this
adapter calls into).
