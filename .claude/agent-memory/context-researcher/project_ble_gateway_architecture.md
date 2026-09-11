---
name: project_ble_gateway_architecture
description:
  Status of BLE gateway hardware validation (ADR-003) and the PM5 relay implementation
  (c2m-ooz.3) — what's proven, what's built, what's left
type: project
---

**Updated 2026-09-11.** This supersedes the previous version of this memory, which was
already stale (described `c2m-ooz.3` as "not started" — it is now software-complete and
twice hardware-validated).

**Decision (ADR-003, `docs/adr/ADR-003-ble-gateway-architecture.md`, Accepted
2026-08-08, amended twice same day):** concept2mqtt holds the sole BLE connection to the
PM5 (hardware-proven: PM5 firmware accepts only one simultaneous BLE central
connection). Two complementary relay mechanisms serve other consumers: an MQTT relay
(not yet built — see [[project_python_app_not_started]]) and a BLE peripheral relay
(concept2mqtt emulates the PM5 on a second adapter) for BLE-native consumers like the
official Concept2 iPhone app.

**Epic `c2m-ooz` (Hardware Validation PoC, P0) status:** `.1` (dual-connection test) and
`.2` (ADR-002... ADR-003) closed. `.3` (the relay implementation) is **in_progress**,
software-complete, hardware-validated twice, with only one child issue left open:
**`c2m-ooz.3.3`** — a hardware re-run of Step C (feature neutrality) + Step D (20-min
stability) + logbook check. This is the single next concrete task on the BLE track and
blocks closing the whole P0 epic. Do it on real hardware (Pi `edge-04`, real PM5, iPhone
with official Concept2 app) — cannot be done in a dev container.

**What's implemented (`packages/concept2mqtt/src/concept2mqtt/ble/`):**

- `profile.py` (386 LOC) — declarative `GattProfile` model, 5 Concept2 proprietary
  services / 27 characteristics, cross-checked at test time against
  `docs/planning/spec/csafe/ble_services.yaml`. An unverified placeholder FTMS profile
  sits behind `get_profile(name)` as a swap point (turned out unneeded — see below).
- `relay.py` (361 LOC) — `BleRelay`: transport-free core wiring a `CentralLink` Protocol
  (real PM5) to a `PeripheralServer` Protocol (emulated PM5), moves opaque bytes, no
  CSAFE decoding (that's a separate concern via the `tap` hook for future MQTT
  publishing). Includes `RelayStats` (notifications_relayed/withheld, write_errors,
  forward_ms_mean, reconnects, etc.) instrumented specifically to diagnose the two
  hardware defects below.
- `errors.py` — `BleRelayError` hierarchy.
- Hardware binding lives at `docs/planning/legacy/examples/relay_pm5.py` (bleak central
  on hci0 + bluez-peripheral peripheral on hci1) — deliberately kept as a PoC script,
  not promoted to `src/` yet.
- 197 unit tests (`packages/concept2mqtt/tests/unit/ble/`, `test_relay.py` alone is 831
  lines) using in-memory `FakeCentralLink`/`FakePeripheralServer` doubles, not mocks.

**Confirmed via 2026-09-05/06 hardware runs (real PM5 serial 530426599, iPhone official
app, Pi `edge-04`):**

- App uses ONLY the proprietary `ce06xxxx` services (identity reads `ce060011-18`, CSAFE
  writes to `ce060021`, sample-rate writes to `ce060034`). Zero FTMS/`0x1826` traffic —
  the FTMS profile placeholder is confirmed unneeded.
- Discovery requires the 128-bit `ce060000` service UUID in the ADV data; `0x1826` alone
  is not seen by the app. Legacy-advertising-only adapters (CSR8510-class dongle) can't
  fit the PM5's full BLE-5 extended-advertising packet (58 B) into 31 B legacy format,
  so the advertised name truncates to "PM5" (documented as a known cosmetic gap).
- Step C (feature neutrality) demonstrated once: live metrics, start/pause/resume/stop,
  splits, end-of-workout summary all relayed correctly, zero notification drops across
  4944 relayed notifications in one session.
- Two defects found and **root-caused and fixed** (2026-09-06, not yet hardware
  re-verified — that's exactly what `c2m-ooz.3.3` covers):
  1. **~1s added latency** (`c2m-ooz.3.1`, closed) — root cause: the app writes an
     8-byte sample-rate value to `ce060034`, a characteristic the spec declares as 1
     byte; the emulated peripheral didn't enforce the length limit, so the PM5 rejected
     the write (ATT `0x0D`) and stayed at its 1 Hz default. Fix: relay now truncates
     over-length consumer writes to the characteristic's declared length before
     forwarding (reproducing the real PM5's own ATT-layer contract). The relay's own
     forward path measured 1.2 ms mean / 4.2 ms max — never the real bottleneck.
  2. **Connection unstable across relay restarts** (`c2m-ooz.3.2`, closed) — three bugs
     in the peripheral binding: a pairing agent left the adapter bondable (iOS cached a
     stale GATT layout after rebinding), `stop()` called a nonexistent
     `Advertisement.release()` method silently swallowed by `contextlib.suppress`, and
     an async `unregister()` call was never awaited. Fixed: non-bondable/non-pairable
     adapter, proper advertisement + GATT app unregistration on shutdown.
  3. Also found/fixed in the same session: SIGINT/SIGTERM were silently ignored under
     `setsid` (no controlling terminal → no `KeyboardInterrupt`), so every prior "clean"
     stop actually left the PM5 connected — now explicit `asyncio` signal handlers.
  4. Auto-reconnect (`c2m-ooz.3.5`, closed) — relay previously never recovered from a
     PM5-side drop (observed stuck for 4h). Fixed with a `disconnected_callback` +
     exponential-backoff reconnect supervisor + `BleRelay.rebind_central()`.

**Full findings log:** `docs/planning/log/pm5-ble-relay-hardware-validation-findings.md`
(through §14.5) — extremely detailed, includes exact BLE traffic tables, requirement
seeds (R-DISC-_, R-PAIR-_, R-LATENCY-_, R-RELAY-_, R-OPS-*), and the reasoning for each
fix. Read this file directly for hardware-debugging-style questions about the relay.

**Acceptance criteria for `c2m-ooz.3`** explicitly do NOT require full feature parity
across every iPhone-app screen (log downloads, workout programming, force plots) — those
live in separate not-yet-built epics `c2m-hlj`/`c2m-2rf`. The relay is byte-level
passthrough; anything not yet exercised would likely pass through fine if the emulated
characteristic set is complete enough.

See also [[project_csafe_codec_architecture]] (separate, unrelated Rust codec track) and
[[project_python_app_not_started]] (the actual concept2mqtt application, which the relay
and codec both feed into but which has no code yet).
