---
status: Accepted
date: 2026-08-08
impact: high
tags: [architecture, devices, mqtt]
---

# ADR-003: BLE Gateway Architecture

## Status

Accepted **Date:** 2026-08-08 | Amended **Date:** 2026-08-08

## Context

concept2mqtt's architecture assumes a single Raspberry Pi acts as the BLE gateway between a Concept2 PM5 rowing monitor and downstream consumers (MQTT/smart-home, and potentially a future coaching app connecting directly). Before committing to this architecture, hardware validation was needed to determine whether the PM5 can maintain more than one simultaneous BLE connection (e.g. concept2mqtt and a phone app both connected at once).

Testing was performed on 2026-08-08 against a real PM5 (serial 530426599) and a Raspberry Pi (aarch64, Debian/Raspberry Pi OS, Python 3.13.5), with the official Concept2 iPhone app holding a connection throughout. Four independent test runs -- three manual, one fully automated (`docs/planning/legacy/examples/test_dual_ble.py`) -- consistently showed: (1) the PM5 stops advertising entirely once any BLE central holds a connection to it, and (2) even a Pi already bonded/paired to the PM5 (giving BlueZ a persistent device object independent of live advertising) cannot establish a second connection -- `bluetoothctl connect` fails after ~40s with `org.bluez.Error.Failed le-connection-abort-by-local`. Before/after scan checks confirmed the iPhone's connection remained active and undisturbed throughout each failed attempt, ruling out the alternative explanation that the failure was actually the iPhone's own link dropping (this false-positive scenario was observed once during testing and is exactly what the bracketing check exists to catch).

## Decision

Use concept2mqtt as the sole BLE gateway to the PM5, relaying all telemetry to other consumers via MQTT, because hardware validation confirmed the PM5 firmware accepts only one simultaneous BLE connection and rejects a second connection attempt at the link layer even from an already-bonded device.

## Decision Drivers

- PM5 firmware accepts only one simultaneous BLE central connection, confirmed via 4 independent hardware tests (issue c2m-ooz.1)
- concept2mqtt already needs to publish decoded telemetry to MQTT for smart-home integration, so a relay is not additive scope
- Future consumers (e.g. a coaching app) must not be permanently blocked from accessing PM5 data
- The connection-owning component is a single point of failure for all PM5 connectivity and must be simple and reliable

## Considered Options

### Option 1: concept2mqtt as sole BLE gateway (MQTT relay) (chosen)

concept2mqtt owns the PM5's single available BLE connection exclusively. All telemetry is decoded via the csafe-codec library and republished on MQTT topics; any other consumer (smart home, a future coaching app, etc.) subscribes to MQTT rather than connecting to the PM5 directly.

- *Advantages:* Matches the confirmed hardware constraint exactly -- no reliance on capabilities the PM5 doesn't have; Single, well-tested connection-owning component; other consumers depend only on MQTT broker uptime; Any number of consumers can subscribe with no additional BLE constraints; No additional scope -- MQTT publishing is concept2mqtt's core purpose anyway
- *Disadvantages:* Adds MQTT hop latency for consumers vs. a hypothetical direct BLE connection; Consumers depend on concept2mqtt and the MQTT broker both being up

### Option 2: Direct multi-consumer BLE

Each consumer (concept2mqtt, a coaching app, etc.) connects to the PM5's BLE GATT server directly and independently, with no relay in between.

- *Advantages:* Lowest possible latency -- no relay hop; No additional component to build or maintain
- *Disadvantages:* Empirically disproven: the PM5 firmware accepts only one simultaneous BLE central connection (issue c2m-ooz.1); Cannot support any second consumer at all, blocking all future direct-BLE integrations

### Option 3: Pi BLE relay (central + peripheral emulation)

The Pi holds the sole real connection to the PM5 (as BLE central) while also emulating a PM5-like BLE peripheral GATT server, so a second local BLE consumer (e.g. a phone app) can connect to the Pi's emulated PM5 instead of the real one, with the Pi proxying notifications and command writes bidirectionally.

- *Advantages:* Lower latency for local BLE consumers than an MQTT round trip; Precedented pattern (e.g. Gymnasticon-style smart trainer relays); PM5 doesn't appear to require pairing-level authentication for its data services, so emulation is plausible
- *Disadvantages:* Significant added complexity: a second full BLE GATT server proxying live data and commands in both directions; Untested whether this Pi's BLE chip supports concurrent central + peripheral roles; Still limited to serving one additional BLE consumer at a time -- doesn't scale like MQTT

## Decision Matrix

| Criterion | concept2mqtt as sole BLE gateway (MQTT relay) | Direct multi-consumer BLE | Pi BLE relay (central + peripheral emulation) |
| --- | --- | --- | --- |
| Hardware feasibility (proven via testing) | 5 | 1 | 3 |
| Implementation complexity | 4 | 5 | 2 |
| Reliability / failure isolation | 5 | 1 | 2 |
| Latency for secondary consumers | 3 | 5 | 4 |
| Extensibility to future consumers | 5 | 1 | 3 |

_Scale: 1 (poor) to 5 (excellent)_

## Consequences

### Positive

- Architecture matches proven hardware behaviour -- no future rework needed from having assumed a second BLE consumer was possible
- Any number of downstream consumers (smart home, future coaching app, logging, etc.) can be added via MQTT topic subscriptions with no BLE constraints
- Single, simple, well-tested connection-owning component reduces the overall failure surface

### Negative

- Consumers needing PM5 data must go through concept2mqtt and the MQTT broker -- no direct low-latency BLE path is available to them
- concept2mqtt becomes a single point of failure for all PM5 connectivity -- if it is down or crashes, no consumer can get PM5 data until it is restarted
- The BLE relay/emulation alternative is deferred rather than ruled out -- if low-latency local consumers become a real requirement, this decision may need revisiting

## Amendment (2026-08-08) — Additive

**Rationale:** Follow-up hardware validation tested the previously-deferred Option 3 (Pi BLE relay) directly, resolving its 'untested' disadvantages with concrete evidence. This does not change the chosen decision (concept2mqtt remains the sole BLE gateway to the PM5) -- it de-risks the alternative for a possible future follow-up feature.

### Additional Sub-Decision: Option 3 (Pi BLE Relay) — Feasibility Update

Same-day follow-up testing (2026-08-08, same Pi and PM5 as the original validation) found and resolved the specific blocker for Option 3, and then confirmed the core concurrency claim directly.

**Root cause found and fixed:** BlueZ's D-Bus `LEAdvertisingManager1` advertisement registration failed with `org.bluez.Error.Failed` / `Invalid Parameters (0x0d)` on this Pi -- reproduced identically on both the onboard Broadcom BCM43430B0 and a CSR8510-class USB dongle, independent of adapter, independent of whether a BLE connection was active, and surviving a full `bluetoothd` restart. This matched a known, tracked upstream kernel regression ([raspberrypi/linux#7473](https://forums.raspberrypi.com/viewtopic.php?p=2381553)) affecting kernel 6.18.x on Pi 4/5/CM5, confirmed system-wide rather than hardware-specific. Fixed via `rpi-update` (`6.18.34+rpt-rpi-v8` → `6.18.42-v8+`); the fix had not yet reached the standard `apt` kernel channel at time of testing. A lower-level `btmgmt`-based advertising workaround was also tried before the root cause was found -- it produced a visible but explicitly non-connectable device (confirmed via the LightBlue iOS app), demonstrating that genuine GATT-server connectability requires the standard D-Bus path, not just raw advertising visibility.

**Concurrency confirmed working post-fix:** with the kernel updated, the Pi held a live central connection to the real PM5 on its onboard adapter (`hci0`) while a second adapter (`hci1`, the CSR8510 USB dongle) ran a real, `bluetoothctl`-registered (D-Bus) GATT peripheral advertisement. An iPhone successfully connected to that peripheral via the LightBlue app while the PM5 connection remained live and unaffected throughout, confirmed by checking `hci0`'s connected-devices list immediately after the iPhone's connection succeeded.

**Confirmed prerequisites for this option:** (1) a second BLE adapter dedicated to the peripheral role -- a CSR8510-class USB dongle is confirmed working; the onboard adapter's ability to sustain both roles alone on a single radio was deliberately not tested and remains an open question, deferred until the two-adapter approach is stable; (2) a kernel build past the raspberrypi/linux#7473 regression window.

**Still open (not addressed by this validation):** the actual relay implementation -- a GATT server replicating enough of the PM5's identity for the official Concept2 iPhone app to accept it, plus bidirectional relaying of notifications and command writes with the real PM5. Working hypothesis, not yet confirmed via traffic capture: the official app queries the proprietary CSAFE-over-BLE service (`ce06xxxx` UUID family) rather than the standard Fitness Machine Service (`0x1826`) the PM5 also exposes; the relay implementation targets the proprietary service on that basis. Tracked as c2m-ooz.3.

## Amendment (2026-08-08) — Corrective

**Rationale:** Today's hardware validation of Option 3 (BLE relay) confirmed it works, and confirmed it is complementary to Option 1's MQTT relay rather than competing with it -- both draw from the same sole PM5 connection concept2mqtt already holds. The original decision text described Option 1 alone as chosen, which doesn't reflect that a BLE peripheral relay is actually needed for BLE-native consumers (e.g. the official Concept2 iPhone app) that cannot speak MQTT at all and would otherwise be locked out entirely. The intended architecture combines both relay mechanisms under the same sole-gateway principle.

> **Justification for amendment (not supersession):** Decision not yet implemented -- concept2mqtt has no BLE gateway code written yet. The relay implementation (c2m-ooz.3) was only just created today and not started, so no downstream code depends on the original single-mechanism wording. Impact is confined to this ADR's decision statement and forward planning; correcting it now avoids building against outdated wording rather than requiring a later supersession.

### Revised Decision

Use concept2mqtt as the sole BLE connection to the PM5, acting as the single gateway for all other consumers of PM5 data and control. Other consumers reach it through two complementary relay mechanisms depending on what they can speak: an MQTT relay for smart-home/dashboard/logging consumers, and a BLE peripheral relay (concept2mqtt emulating the PM5 on a second BLE adapter) for BLE-native consumers that cannot speak MQTT at all, such as the official Concept2 iPhone app. These two mechanisms are not competing alternatives -- both draw from the same sole PM5 connection concept2mqtt already holds, and hardware validation (see the 2026-08-08 additive amendment above) confirmed both are technically viable together.

### Additional Sub-Decision: Reclassifying Options 1 and 3 as complementary, not competing

The original decision matrix scored Option 1 (MQTT relay) and Option 3 (BLE peripheral relay) as if choosing one meant not doing the other. In practice they are not mutually exclusive: both mechanisms sit on top of the same 'concept2mqtt holds the sole PM5 connection' principle established by ruling out Option 2. Option 1 serves consumers that can speak MQTT; Option 3 serves BLE-native consumers that cannot. The chosen architecture is now Option 1 AND Option 3 together, tracked for implementation as c2m-ooz.3. Option 2 (direct multi-consumer BLE) remains ruled out, empirically disproven by the PM5 hardware itself.

### Additional Positive Consequences

- The official Concept2 iPhone app continues to work alongside concept2mqtt, rather than being permanently locked out under a pure MQTT-only relay -- MQTT-speaking consumers (dashboards, smart home, big-screen displays) and the BLE-native app can be used at the same time

### Additional Negative Consequences

- concept2mqtt now needs to build and maintain two relay mechanisms (MQTT publisher and a BLE peripheral GATT server) instead of one, increasing implementation and long-term maintenance surface
- The BLE peripheral relay depends on a second BLE adapter and a kernel build past a known regression (see additive amendment above) -- additional hardware/OS prerequisites beyond the MQTT-only path
