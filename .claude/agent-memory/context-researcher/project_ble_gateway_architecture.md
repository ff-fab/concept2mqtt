---
name: project_ble_gateway_architecture
description:
  Status of BLE gateway hardware validation (ADR-003) and the PM5 dual-connection PoC —
  what's proven, what's next
type: project
---

Hardware validation for the BLE gateway architecture (epic `c2m-ooz`, P0) is 2/3
complete as of 2026-08-08.

**Proven facts (via `docs/planning/legacy/examples/test_dual_ble.py`, commit
`680a723`):**

- PM5 firmware accepts only ONE simultaneous BLE central connection. Confirmed via 4
  independent test runs against a real PM5 (serial 530426599) on a Pi, with the iPhone
  Concept2 app connected.
- Follow-up same-day testing found the Pi's onboard BLE adapter fails to register a
  peripheral GATT advertisement on kernel 6.18.x (upstream regression
  raspberrypi/linux#7473, `Invalid Parameters 0x0d` from BlueZ's
  `LEAdvertisingManager1`). Fixed via `rpi-update` to `6.18.42-v8+`.
- After the kernel fix, dual-role operation (hci0 = central to real PM5, hci1 = USB
  CSR8510 dongle running a real GATT peripheral) was confirmed working — an iPhone
  connected to the emulated peripheral via LightBlue while the PM5 connection on hci0
  stayed live.

**Decision (ADR-003, `docs/adr/ADR-003-ble-gateway-architecture.md`, Accepted + amended
twice same day):** concept2mqtt is the sole BLE connection to the PM5. Two complementary
(not competing) relay mechanisms serve other consumers: an MQTT relay for MQTT-speaking
consumers, and a BLE peripheral relay (concept2mqtt emulating the PM5 on a second
adapter) for BLE-native consumers like the official Concept2 iPhone app that can't speak
MQTT at all.

**Issue state:**

- `c2m-ooz.1` (run the dual-connection test) — CLOSED, produced the finding above.
- `c2m-ooz.2` (write the ADR) — CLOSED, produced ADR-003.
- `c2m-ooz.3` (implement the actual relay: Pi central + peripheral emulation on 2
  adapters, byte-level passthrough, `bluez-peripheral` lib, D-Bus GattManager1/
  LEAdvertisingManager1 path not raw btmgmt) — OPEN, P2, not started. This is the last
  child of the `c2m-ooz` epic and the next concrete BLE-track work item.

**Why this matters:** `docs/planning/legacy/examples/test_dual_ble.py` is a hardened
diagnostic/PoC script (502 lines, has a full phase-based test harness with
scan/bonded-fallback/connect/GATT-read/notification-subscribe/manual-iPhone-check
phases), not application code — it lives under `docs/planning/legacy/examples/`, not
`src/`. It fully served its diagnostic purpose (closed c2m-ooz.1) and should not be
mistaken for a component that still needs finishing; the actual relay implementation is
a separate, not-yet-started task (c2m-ooz.3).

**How to apply:** When asked "what's next" on the BLE track, the answer is `c2m-ooz.3` —
it has a fairly detailed DESIGN section already in beads (hypothesis: emulate the
proprietary `ce06xxxx` CSAFE service, not the standard Fitness Machine Service `0x1826`;
unconfirmed without a BLE traffic capture of the real app). Note this depends on the
same hexagonal `Pm5Port` scaffolding work (`c2m-x3b` epic) also being built in parallel
— check both epics before recommending where to start next.

**Scope caveat (checked 2026-08-27):** c2m-ooz.3's 5 acceptance criteria cover
connect/identity emulation, live-data relay latency, command relay, unaffected MQTT
publishing, and hci0 connection stability for an extended session — they do NOT state or
require full "feature parity/neutrality" with a direct iPhone-to-PM5 connection (no
criterion enumerates testing every app feature, e.g. log downloads, workout programming,
force plots — those live in separate not-yet-built epics `c2m-hlj`/`c2m-2rf`). The relay
is byte-level passthrough (no CSAFE decoding needed for the relay itself), so untested
features would likely pass through fine IF the emulated GATT service/characteristic set
is complete enough — but that completeness is exactly what's unverified. The
proprietary-vs-standard CSAFE service hypothesis (`ce06xxxx` vs `0x1826`) remains
explicitly unconfirmed without a real BLE traffic capture (e.g. Xcode PacketLogger) — if
wrong, the app may not even recognize the relay as a PM5. As of this check there is no
separate/later beads issue for "iPhone app validation" or "feature parity testing"
anywhere in `bd list` (35 issues total) — c2m-ooz.3 is the terminal child of the
`c2m-ooz` epic; closing it closes the epic. The nearest adjacent item, `c2m-j2s.4`
("End-to-end MVP validation on real Pi hardware", epic `c2m-j2s` MVP Integration),
validates concept2mqtt's own telemetry pipeline, not iPhone-app-via-relay parity.
