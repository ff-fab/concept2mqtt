# Concept2mqtt — Design Sparring

This document challenges the initial feature plan, maps PM5 capabilities to
cosalette concepts, proposes a refined feature set, and identifies open
questions. It is a **deliberation document** — not a plan.

---

## 1. Challenging the Feature Plan

### 1.1 "Get all historical training data"

The feature plan describes syncing all stored workout logs from the PM5.
This is **significantly more complex** than it appears:

**What the PM5 actually stores:**

- The PM5 has limited internal memory. Workout log entries are stored in flash
  and can be retrieved via proprietary CSAFE commands (`PM_GET_LOGENTRY_DATA`,
  `PM_GET_LOGENTRY_SPLITINTERVALDATA`, etc.).
- The spec documents a max of ~70-80 workout log entries (memory-dependent).
- Older workouts are overwritten by newer ones — the PM5 is **not** an archival
  store.
- The PM5 does NOT have a "what's new since timestamp X" query — you'd need to
  enumerate entries and compare against what you've seen before.

**Challenge: Who owns the sync state?**

The feature plan says _"Master data shall be the data stored by the smart home
system."_ This is the right instinct, but it means **concept2mqtt should NOT
track sync state**. It should be a **dumb pipe**: retrieve what's asked for,
publish it to MQTT, done. The downstream consumer (Home Assistant, a database,
etc.) is responsible for deduplication and persistence.

Why? Because sync-state in the bridge means:
- The bridge needs persistent local storage (bad for a Pi Zero — SD card wear,
  crash recovery, state corruption)
- The bridge becomes a stateful service instead of a stateless bridge
- Two sources of truth create reconciliation complexity

**Challenge: When do you sync?**

The PM5 hibernates. It only wakes when:
- The flywheel is pulled (mechanical wake-up signal)
- A button is pressed on the PM5 itself
- (Possibly) a BLE connection attempt during a [brief advertising window]

This means **you cannot trigger a sync remotely on demand**. The sync window is
whenever the PM5 happens to be awake. Options:

| Strategy | Pros | Cons |
| --- | --- | --- |
| **Sync-on-connect** | Simple, deterministic — every time we see the PM5, dump logs | May be slow (60+ entries × CSAFE round-trips), delays live telemetry start |
| **Sync-on-command** | User triggers via MQTT/HA button when PM5 is known awake | Requires manual action; PM5 may hibernate during sync |
| **Sync-after-workout** | Detect workout end → immediately pull latest log | Most natural; only grabs new data; PM5 is guaranteed awake |
| **Background sync** | Incrementally pull logs while idle between workouts | Complex; must not interfere with live telemetry |

**Recommendation:** Sync-after-workout as the primary mechanism, with
sync-on-command as the manual fallback. Sync-on-connect is appealing but may
not be desirable if the user just wants to row — you don't want a 30-second
CSAFE log dump before live telemetry starts.

### 1.2 "Get live training data"

This is more straightforward but has hidden complexity:

**What's available via BLE notifications (passive — no CSAFE needed):**

| Characteristic | UUID suffix | Key fields | Update rate |
| --- | --- | --- | --- |
| General Status | 0x0031 | elapsed time, distance, workout/rowing/stroke state, drag factor | 500ms default |
| Additional Status 1 | 0x0032 | speed, stroke rate, heart rate, current pace | 500ms |
| Additional Status 2 | 0x0033 | split interval data, interval power, calories | 500ms |
| Stroke Data | 0x0035 | drive length, drive time, stroke recovery, stroke distance, peak force | per-stroke |
| Extra Status 1 | 0x0036 | projected finish time, calories/hour, state transitions | on change |
| Extra Status 2 | 0x0038 | more split data | on change |
| General Status + Multiplexed | 0x0039 | all of General Status + rotating multiplexed extension data | 500ms |
| Additional Status + Multiplexed | 0x003A | all of Additional 1 + rotating multiplexed extension | 500ms |

**What requires CSAFE polling (active):**

| Data | Command | Notes |
| --- | --- | --- |
| Force plot data | `PM_GET_FORCEPLOTDATA` | 32 bytes max per request, high frequency needed for full curve |
| Heart beat data | `PM_GET_HEARTBEATDATA` | Individual heart beats (R-R intervals) |
| Workout log entries | `PM_GET_LOGENTRY_*` | Historical data (not live) |

**Challenge: MQTT publish rate**

At 500ms intervals across 4+ characteristics, that's 8+ MQTT messages/second.
At 100ms it's 40+/second. This is fine for a local broker but raises questions:

- Should characteristics be **merged into fewer, richer MQTT messages**? (e.g.
  one `concept2mqtt/pm5/state` JSON blob every 500ms combining all
  characteristics, vs. one topic per characteristic)
- What's the right balance between **granularity** (separate topics per metric)
  and **efficiency** (fewer, larger payloads)?
- Should concept2mqtt support **configurable publish rates** independently of
  the BLE subscription rate?

**Challenge: Force plot data**

Force plot data is the per-stroke force curve — the "shape" of each stroke.
This is **high-value for coaching** but requires CSAFE round-trip polling (not
passive notification). Each request returns max 32 bytes (16 force values). A
full stroke curve can be 40-60+ samples, requiring multiple requests per
stroke at ~1 stroke/second.

This creates a tight timing loop that may conflict with other CSAFE operations
(log retrieval, status queries). It's also the most CPU/BLE-intensive feature.

**Recommendation:** Support force plot data as an **opt-in feature**, disabled
by default. It's the killer feature for coaching apps but not needed for basic
smart home integration.

### 1.3 Missing from the feature plan

Several capabilities the PM5 offers that the plan doesn't mention:

1. **Workout programming** — The PM5 can be programmed with custom workouts
   via CSAFE. This turns concept2mqtt into a **bidirectional bridge** (not
   just read-only). A Home Assistant dashboard could let you configure and
   start workouts.

2. **Heart rate monitor passthrough** — The PM5 pairs with ANT+ HR monitors and
   exposes the HR data via BLE notifications and CSAFE. concept2mqtt could
   relay HR data without needing a separate HR→MQTT bridge.

3. **Date/time sync** — The PM5 has a clock that drifts. Setting it via CSAFE
   (`PM_SET_DATETIME`) on each connection would keep it accurate.

4. **Drag factor reporting** — The drag factor changes as the damper setting or
   air conditions change. Publishing it helps compare effort across sessions.

5. **Error log retrieval** — The PM5 stores error logs (747 documented error
   codes!). Useful for diagnostics/maintenance.

6. **Machine identification** — Serial number, firmware version, hardware
   revision, machine type (rower, SkiErg, BikeErg). concept2mqtt should
   identify what it's connected to.

---

## 2. Cosalette Fit Analysis

### 2.1 Why cosalette is a good fit

concept2mqtt is textbook cosalette territory: an IoT device (PM5) bridged to
MQTT. The framework handles exactly the boilerplate we'd otherwise write:

- MQTT lifecycle, LWT, reconnection
- Structured logging (JSON for production — good for Pi Zero log shipping)
- Health reporting (PM5 availability → Home Assistant)
- CLI flags (--dry-run, --log-level)
- Error isolation
- Graceful shutdown (SIGTERM from systemd/Docker)

### 2.2 Which device archetype?

The PM5 is a **hybrid device** — it streams telemetry AND accepts commands.
This rules out `@app.telemetry` (unidirectional) and `@app.command`
(per-message, no long-running loop). The PM5 needs:

- A long-running BLE connection management loop
- Active notification subscription management
- CSAFE command/response interleaving
- Workout state machine tracking
- Adaptive behaviour based on PM5 state (idle → workout → post-workout)

**Verdict:** `@app.device("pm5")` is the appropriate archetype. This gives us:

- Full coroutine control (the BLE event loop)
- `@ctx.on_command` for inbound MQTT commands (sync history, start workout,
  etc.)
- Manual `ctx.publish_state()` for outbound telemetry
- `ctx.shutdown_requested` + `ctx.sleep()` for graceful lifecycle

### 2.3 Port/Adapter design

Cosalette's hexagonal architecture maps cleanly:

```
┌─────────────────────────────────────────┐
│              concept2mqtt               │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  PM5 Device Logic               │    │
│  │  (@app.device coroutine)        │    │
│  │                                 │    │
│  │  Uses: BlePort, CsafePort      │    │
│  └────────┬──────────┬─────────────┘    │
│           │          │                  │
│     ┌─────┴─────┐ ┌──┴──────────┐      │
│     │ BlePort   │ │ CsafePort   │      │
│     │ (Protocol)│ │ (Protocol)  │      │
│     └─────┬─────┘ └──┬──────────┘      │
│           │          │                  │
│     ┌─────┴─────┐ ┌──┴──────────┐      │
│     │ BleakAdpt │ │ CsafeCodec  │      │
│     │ (bleak)   │ │ (framing)   │      │
│     └───────────┘ └─────────────┘      │
└─────────────────────────────────────────┘
```

**Ports to define:**

| Port | Responsibility | Production adapter | Test double |
| --- | --- | --- | --- |
| `BlePort` | Scan, connect, disconnect, read characteristic, subscribe to notifications | `BleakAdapter` (wraps bleak) | `FakeBleAdapter` (in-memory, recorded responses) |
| `CsafePort` | Frame/unframe CSAFE, send command, receive response | `BleakCsafeAdapter` (write/read via BLE characteristics) | `FakeCsafeAdapter` (canned responses) |

**Key design question:** Should CSAFE framing be in the adapter or in a
separate codec layer? The CSAFE frame format (byte stuffing, checksum, command
packing) is **pure logic** — no I/O — so it's testable as a standalone module.
The adapter only handles BLE write/read with a pre-framed byte array.

**Recommendation:** CSAFE codec as a pure domain module (no port needed).
The `BlePort` adapter handles BLE I/O, the codec handles framing. This gives
us maximum test coverage on the tricky byte-manipulation code without needing
any BLE mock.

### 2.4 Lazy imports for bleak

Cosalette's lazy import pattern is critical here. `bleak` depends on
`dbus-fast` on Linux and heavy platform-specific C libraries. We want:

```python
app.adapter(
    BlePort,
    "concept2mqtt.adapters.bleak:BleakAdapter",     # lazy
    dry_run="concept2mqtt.adapters.fake_ble:FakeBle" # dry-run
)
```

This means `bleak` is never imported during `pytest` collection on a dev
machine (no dbus, no Bluetooth stack needed), and dry-run mode works on any
platform.

---

## 3. Proposed Feature Set (Thin Enabler)

concept2mqtt's philosophy: **publish everything, control nothing (initially).**
Be a maximally useful, thin data bridge. Let downstream apps decide what to do
with the data.

### 3.1 Core features (MVP)

| # | Feature | Complexity | Value |
| --- | --- | --- | --- |
| F1 | **PM5 discovery & connection** — Scan BLE for PM5 devices, connect to configured (or first-found) PM5, manage BLE connection lifecycle | Medium | Required foundation |
| F2 | **Device identity** — Read & publish serial number, firmware, hardware rev, machine type, drag factor | Low | Foundation |
| F3 | **Live workout telemetry** — Subscribe to BLE notification characteristics during workout, decode and publish to MQTT | High | Core value |
| F4 | **Workout lifecycle events** — Detect workout start/end/pause/resume from state transitions, publish events | Medium | Required for sync |
| F5 | **Post-workout log retrieval** — After workout end, pull the latest log entry via CSAFE and publish to MQTT | Medium-High | Key data feature |
| F6 | **Health & availability** — Use cosalette health reporting for PM5 online/offline based on BLE connection state | Low | HA integration |
| F7 | **CSAFE codec** — Full encode/decode for the CSAFE wire protocol (byte stuffing, checksum, command packing) | Medium | Foundation |

### 3.2 Extended features (post-MVP)

| # | Feature | Complexity | Value |
| --- | --- | --- | --- |
| F8 | **Full log history sync** — On-demand dump of all stored workout logs | Medium | Data completeness |
| F9 | **Force plot data** — Per-stroke force curve via CSAFE polling (opt-in) | High | Coaching apps |
| F10 | **Heart rate passthrough** — Relay HR from PM5's ANT+ paired monitor | Low | Convenience |
| F11 | **Date/time sync** — Set PM5 clock on each connection | Low | Maintenance |
| F12 | **Workout programming** — Accept workout config via MQTT, program PM5 | Very High | Bidirectional control |
| F13 | **Error log retrieval** — Pull PM5 error log on demand | Low | Diagnostics |
| F14 | **Home Assistant MQTT Discovery** — Publish HA auto-discovery config messages | Medium | Plug-and-play HA |

### 3.3 Proposed MQTT topic layout

Following cosalette conventions (`{app}/{device}/{channel}`):

```
concept2mqtt/pm5/state               ← aggregated live telemetry (JSON)
concept2mqtt/pm5/availability         ← "online" / "offline"
concept2mqtt/pm5/error                ← structured error events
concept2mqtt/pm5/set                  ← inbound commands

concept2mqtt/pm5/identity/state       ← device info (serial, FW, HW, machine type)
concept2mqtt/pm5/workout/state        ← workout lifecycle events (started, ended, paused)
concept2mqtt/pm5/stroke/state         ← per-stroke data (drive length, peak force, etc.)
concept2mqtt/pm5/log/{entry_id}/state ← individual workout log entries
concept2mqtt/pm5/force_plot/state     ← force curve data (opt-in)

concept2mqtt/status                   ← app heartbeat / LWT
concept2mqtt/error                    ← global error events
```

**Architecture question:** cosalette's model is `{app}/{device}/state` — one
state topic per device. The PM5 produces **multiple concurrent data streams**
at different rates. Options:

**Option A: Single fat state topic**
All live data merged into one `concept2mqtt/pm5/state` JSON blob published at
the fastest rate. Simple, but the payload is large and mixing fast-changing
(distance, time) with static data (drag factor, machine type) wastes bandwidth.

**Option B: Multiple sub-devices**
Register each data stream as a separate cosalette device:
`@app.telemetry("general_status", ...)`,
`@app.telemetry("stroke_data", ...)`, etc. Clean topic separation, but the
BLE connection is shared — how do we share the BlePort adapter across devices?

**Option C: Single `@app.device` with multiple manual publishes**
One `@app.device("pm5")` coroutine that calls `ctx.publish()` to multiple
custom topic paths. Total control, but bypasses some cosalette conventions.

**Recommendation:** Option C with a structured topic tree as shown above. The
PM5's data model is complex enough that it doesn't cleanly map to cosalette's
"one device, one state topic" model. A single `@app.device` manages the BLE
connection and uses `ctx.publish()` with different sub-topics. This is the
"escape hatch" pattern that cosalette explicitly supports.

---

## 4. Future Projects (Building on concept2mqtt)

concept2mqtt's value increases when other apps consume its MQTT streams.
By keeping concept2mqtt thin and data-rich, we enable:

### 4.1 concept2coach (Real-time coaching app)

- Subscribes to `concept2mqtt/pm5/state` and `concept2mqtt/pm5/stroke/state`
- Provides real-time audio/visual feedback: pacing, stroke rate targets,
  split comparisons
- Force plot analysis for technique coaching
- Could be a web app (Flask/FastAPI + WebSocket) or a native app
- **concept2mqtt dependency:** Live telemetry topics + force plot data

### 4.2 concept2stats (Historical analysis)

- Subscribes to `concept2mqtt/pm5/log/+/state` for workout logs
- Persists to a database (InfluxDB, TimescaleDB, SQLite)
- Trend analysis: pace over time, consistency, volume
- Comparison with Concept2 logbook (API integration)
- **concept2mqtt dependency:** Workout log topic + workout lifecycle events

### 4.3 concept2race (Virtual racing)

- Subscribes to live telemetry from multiple concept2mqtt instances
  (one per rower)
- Real-time side-by-side race visualization
- Replay mode: race against your own past workouts
- **concept2mqtt dependency:** Live telemetry + workout lifecycle events

### 4.4 Home Assistant integration

- Entities: current pace sensor, distance sensor, heart rate sensor,
  workout binary sensor, PM5 connection status
- Automations: "When workout starts, dim lights and start Spotify playlist"
- **concept2mqtt dependency:** All topics + HA MQTT discovery messages (F14)

---

## 5. Open Questions

These need answers before we can draft the detailed architecture:

### 5.1 Hardware & Connectivity

**Q1. Single PM5 or multi-PM5 support?**
Will concept2mqtt ever connect to >1 PM5 simultaneously? This dramatically
affects architecture (connection pooling, topic namespacing). My recommendation:
start single-PM5, but design the topic layout to be extensible
(`concept2mqtt/{serial_or_name}/...`).

**Q2. Pi Zero 2 W BLE bandwidth?**
The Pi Zero 2 W has a Bluetooth 4.2 radio. With 4+ concurrent BLE notification
subscriptions at 500ms + CSAFE polling, is the radio bandwidth sufficient?
Need validation on the real hardware. The BLE 4.2 max throughput is ~1 Mbit/s,
which is plenty for this data volume, but bleak's event loop overhead on a
single-core ARM is the real constraint.

**Q3. Always-on vs on-demand connection?**
Should the app constantly scan for the PM5 and connect when available? Or
should it only connect when activated? Battery isn't a concern for a wired PM5
(coin cell only for the clock), but the PM5 may not advertise when hibernating.

**Q4. BLE connection stability?**
The smoke test shows BLE connections to the PM5 can be finicky
(disconnect races, notification subscription timing). How resilient does the
reconnection logic need to be? The PM5 may drop the BLE connection during
certain state transitions (firmware updates, menu navigation).

### 5.2 Data & Sync

**Q5. Do you use the Concept2 online logbook?**
If you upload workouts to Concept2's servers (via ErgData app or USB), the
online logbook may already have a more complete history than the PM5's memory.
Would a Concept2 API integration (separate project) be more valuable than
PM5-direct log retrieval?

**Q6. Is workout log sync a hard requirement for MVP?**
Log retrieval via CSAFE is complex (multi-step, paginated, byte-level
parsing). Live telemetry is more immediately useful and much simpler. Could
MVP ship with live telemetry only and add log sync later?

**Q7. What data resolution is needed?**
The PM5 can send notifications at 100ms, 250ms, 500ms, or 1s. For a smart
home dashboard, 1s is plenty. For a coaching app, 250ms may be needed. For
force plots, you need per-stroke resolution (~1/sec). What's the target?

### 5.3 Architecture

**Q8. Workout programming — in scope at all?**
Programming workouts via MQTT commands (F12) is powerful but turns concept2mqtt
from a read-mostly bridge into a bidirectional control surface. This has
security implications (someone could remotely reprogram your workout) and UX
implications (error recovery if the PM5 is in the wrong state). In or out?

**Q9. Home Assistant auto-discovery — MVP or later?**
HA MQTT Discovery publishes auto-config messages so entities appear in HA
without manual YAML. It's a Medium effort but huge UX win. Worth including
in MVP?

**Q10. Force plot data — needed at all?**
Force plots are the most complex, BLE-intensive feature. They require tight
CSAFE polling loops incompatible with other operations. Are they worth having
in concept2mqtt, or should a coaching app connect to the PM5 directly for
this data?

### 5.4 Deployment

**Q11. systemd service or Docker container?**
On a Pi Zero 2 W, Docker adds significant overhead. systemd is lighter.
Cosalette supports both, but it affects packaging (`.deb`? `uv tool`?
`pipx`?).

**Q12. Mosquitto colocation?**
Will the MQTT broker run on the same Pi as concept2mqtt? If yes, localhost
comms. If not, network reliability between the Pi and the broker becomes a
concern.

---

## 6. Additional Resources & References

### 6.1 Existing PM5 open-source projects

These projects have solved (or attempted) many of the problems we'll face.
Worth studying for implementation patterns and pitfalls:

- **py-concept2** / **pyrow** — Python libraries for PM5 USB communication.
  USB uses the same CSAFE protocol, different transport.
- **pROWess** — The cross-references in your CSAFE spec. A Python PM5 BLE
  library. Studied its `frameCSAFE()` / `unframeCSAFE()` and notification
  decoding for validation against the spec.
- **c2bluetooth** (Dart) — The other cross-reference in the spec. A Flutter
  PM5 BLE library. Useful for validating enum values and BLE UUID usage.
- **ErgData** (Concept2's own iOS/Android app) — The official app. Set a
  benchmark for what's possible.
- **CrewNerd** — Third-party rowing app that connects to PM5 via BLE. Good
  reference for UX and data display.

### 6.2 BLE on Pi Zero 2 W

- `bleak` 0.22+ has good Linux/BlueZ support but requires `dbus-fast`
- BlueZ 5.66+ recommended for BLE stability
- `bluetoothctl` for manual debugging
- Pi Zero 2 W has BCM43436s — BLE 4.2 (sufficient for PM5, which is also 4.2)

### 6.3 CSAFE protocol considerations

- Max frame size: 120 bytes including overhead
- Min inter-frame gap: 50ms — this fundamentally limits CSAFE query rate
  to ~20 commands/second
- No ACK/NAK at frame level — errors detected by missing/malformed responses
- Multiple commands can be packed into a single frame (saves round-trips)
- BLE characteristic length: 20 bytes per write — large frames need
  segmentation across multiple BLE writes (ATT MTU negotiation may help)

---

## 7. Recommendation: Next Steps

1. **Answer the open questions** (§5) — especially Q1, Q3, Q6, Q7, Q8
2. **Validate BLE assumptions** on real hardware — extend the smoke test to:
   - Subscribe to all notification characteristics simultaneously
   - Measure notification delivery timing under load
   - Test CSAFE round-trip latency
   - Test reconnection after PM5 sleep/wake
3. **Draft the detailed architecture** — once questions are resolved, produce:
   - ADR for device archetype choice
   - ADR for topic layout
   - ADR for CSAFE codec design (pure logic vs adapter)
   - Port/adapter interface definitions
4. **Build the CSAFE codec first** — it's pure logic, 100% testable without
   hardware, and everything else depends on it
5. **Build connection management second** — PM5 discovery, connect/disconnect,
   health reporting
6. **Add live telemetry third** — BLE notification subscriptions, data
   decoding, MQTT publishing
7. **Add log retrieval last** — complex, depends on CSAFE codec + connection
   management
