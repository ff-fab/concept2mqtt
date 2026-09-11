---
name: project_python_app_not_started
description:
  The core concept2mqtt Python application (MQTT publishing, Pm5Port adapter) has no
  implementation yet — only supporting infrastructure exists
type: project
---

As of 2026-09-11: `packages/concept2mqtt/src/concept2mqtt/main.py` is a literal `# TODO`
— the actual application entrypoint does not exist. What _is_ implemented in
`packages/concept2mqtt/src/concept2mqtt/` is only:

- `config.py` — a `pydantic-settings` `Settings` class (log_level, host, port — port
  defaults to 1883, MQTT-broker-shaped, but there is no MQTT client code anywhere).
- `ble/` — the BLE peripheral relay subsystem, see [[project_ble_gateway_architecture]].

Three beads epics constitute the real, unbuilt product (14 open issues total, all P1/P2,
none started as of this writing):

- **`c2m-x3b`** "App Scaffold — cosalette + Pm5Port" — define the `Pm5Port` Protocol
  (domain types + exception hierarchy), a `FakePm5Adapter` test double, scaffold the
  `cosalette` app structure (`@app.device`, adapter registration, settings, lifespan),
  define MQTT topic layout in code, and an ADR for the Pm5Port hexagonal architecture
  (Option C). This is the foundational scaffold everything else depends on.
- **`c2m-bm7`** "BLE Adapter — BleakPm5Adapter" — the actual bleak-based adapter
  implementing `Pm5Port`: scanning/connection/reconnection state machine, device
  identity reads (GATT 0x0011–0x0015), notification subscription wired to the Rust
  decoders, CSAFE request/response (50ms inter-frame gap), notification-rate
  configuration (char 0x0034). Depends on `c2m-x3b`.
- **`c2m-j2s`** "MVP Integration — Live Telemetry Pipeline" — workout lifecycle state
  machine from notifications, live telemetry publishing (`pm5/state`, `pm5/stroke/state`
  QoS 0), health/availability (cosalette health, LWT, retained), and end-to-end MVP
  validation on real Pi hardware. This is the actual "mqtt" in concept2mqtt.

**Why this matters:** everything closed in beads so far (see `bd list`) is either the
Rust CSAFE codec (`c2m-7wu`/`c2m-m05`/`c2m-dn9`/`c2m-cyu` epics) or the BLE
relay/hardware-validation track (`c2m-ooz`) — i.e. protocol/infrastructure layers. The
Python application layer that would make concept2mqtt actually publish PM5 telemetry to
MQTT has zero code. When asked "what's the core app status" or "where's the MQTT
publishing", the answer is: not started, tracked as `c2m-x3b`/`c2m-bm7`/`c2m-j2s`, and
`c2m-x3b` (app scaffold) is the correct starting point since the other two depend on it.

"cosalette" is referenced repeatedly in these issues as the intended app framework but
does not appear anywhere in the current codebase or `pyproject.toml` dependencies —
verify it's an available/intended dependency before starting `c2m-x3b` work.
