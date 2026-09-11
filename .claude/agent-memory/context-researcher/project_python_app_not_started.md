---
name: project_python_app_scaffold
description:
  The concept2mqtt Python application scaffold defines its MQTT-facing PM5 port; the
  real BLE adapter and hardware validation remain unimplemented
type: project
---

As of 2026-09-11, `packages/concept2mqtt/src/concept2mqtt/` includes a runnable CLI
entry point, a cosalette application scaffold, PM5 domain types and port, MQTT topic
policy, and `FakePm5Adapter`. The CLI deliberately does not register a production
adapter until `BleakPm5Adapter` exists. The remaining implementation is:

- `ble/` — the BLE peripheral relay subsystem, see [[project_ble_gateway_architecture]].

Three beads epics constitute the real, unbuilt product (14 open issues total, all P1/P2,
none started as of this writing):

- **`c2m-x3b`** "App Scaffold — cosalette + Pm5Port" — completed: the port, domain
  types, fake adapter, application scaffold, MQTT topic policy, and ADR now exist.
- **`c2m-bm7`** "BLE Adapter — BleakPm5Adapter" — the actual bleak-based adapter
  implementing `Pm5Port`: scanning/connection/reconnection state machine, device
  identity reads (GATT 0x0011–0x0015), notification subscription wired to the Rust
  decoders, CSAFE request/response (50ms inter-frame gap), notification-rate
  configuration (char 0x0034). Depends on `c2m-x3b`.
- **`c2m-j2s`** "MVP Integration — Live Telemetry Pipeline" — workout lifecycle state
  machine from notifications, live telemetry publishing (`pm5/state`, `pm5/stroke/state`
  QoS 0), health/availability (cosalette health, LWT, retained), and end-to-end MVP
  validation on real Pi hardware. This is the actual "mqtt" in concept2mqtt.

**Why this matters:** the app scaffold can publish domain events using a fake adapter,
but no real PM5 BLE transport is registered. `c2m-bm7` and `c2m-j2s` remain the work
needed to connect hardware and validate the live telemetry pipeline.

Cosalette is the application framework declared in `pyproject.toml`.
