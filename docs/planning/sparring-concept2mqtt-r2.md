# Concept2mqtt — Design Sparring (Round 2)

This document refines the concept2mqtt design based on Round 1 feedback.
It incorporates confirmed decisions, adds deep-dive elaborations on requested
topics, and narrows the remaining open questions.

**Document purpose:** Deliberation and sparring — not a work plan.

---

## Status of Round 1 Decisions

| Topic | Decision | Notes |
| --- | --- | --- |
| State ownership | Stateless bridge (downstream owns persistence) | Minor local state OK to prevent flooding |
| Sync strategy | Sync-after-workout + on-demand trigger | On-demand trigger = "dump all logs" for initial setup |
| Live telemetry | During workout, at PM5-native frequency | Details in §2 (update rate deep-dive) |
| MVP scope | Live telemetry only | Log sync moves to fast-follow, not MVP |
| Full log dump | In plan, not MVP | Needed for smart home initial setup |
| PM5 count | Single PM5 | Topic layout should be extensible |
| Workout programming | In scope (post-MVP) | Bidirectional bridge |
| HA MQTT Discovery | In plan, not MVP | Monitor cosalette framework readiness |
| Deployment | Defer decision, offer both systemd & Docker | |
| MQTT broker | Remote (strong machine) | Network latency is a factor |
| Concept2 online logbook | Separate project; doesn't replace local data capture | |
| Connection resilience | High — robust reconnection required | Firmware updates/menu transitions acceptable |

---

## 1. Deep Dive: BLE Scanning Behaviour & PM5 Wake/Sleep

### 1.1 How BLE scanning works (and doesn't wake peripherals)

BLE scanning is a **central-side** operation. The scanner (Pi) listens on the
three advertising channels (37, 38, 39) for advertising packets that
peripherals broadcast.

There are two scan types:

| Scan type | Central behaviour | Impact on peripheral |
| --- | --- | --- |
| **Passive scan** | Listen only — never transmits | **Zero impact.** Peripheral doesn't know it's being observed. |
| **Active scan** | After receiving ADV_IND, sends SCAN_REQ to get scan response data | **Minimal impact.** Peripheral replies with scan response (trivial energy). |

**Key insight: scanning does NOT wake a sleeping peripheral.** A BLE peripheral
in deep sleep simply does not advertise, so there is nothing to scan for. The
scanner hears silence. Only when the PM5 wakes (flywheel pulled, button
pressed) does it begin advertising and become discoverable.

### 1.2 PM5 advertising behaviour

The PM5 uses BLE 4.2 with the nRF52 chipset. Based on the spec and observed
behaviour:

- **When awake** (user interacts, flywheel pulled): PM5 advertises using
  connectable undirected advertising (`ADV_IND`). Device name includes "PM5"
  prefix plus serial number.
- **When hibernating**: PM5 stops advertising entirely. It enters deep sleep
  to conserve the coin cell battery (used for the clock).
- **Advertising interval**: Typical BLE peripherals use 20ms–10s. PM5 likely
  uses a moderate interval (100ms–1s) when awake. We can measure on hardware.

### 1.3 Impact on the scanning device (Pi Zero 2 W)

Continuous passive scanning has **modest** impact on the Pi:

| Resource | Passive scan | Active scan |
| --- | --- | --- |
| CPU | Minimal — BlueZ handles in kernel | Slightly higher (processes SCAN_RSP) |
| Power draw | ~10-20mW additional for BLE radio | Same |
| BLE radio time | Receiver on, transmitter off | Brief TX for each SCAN_REQ |

In BLE 4.2, the central can scan with a configurable duty cycle
(`scan_window` / `scan_interval`). Default bleak settings are typically:
- `scan_interval` = 11.25ms
- `scan_window` = 11.25ms (100% duty cycle)

For always-on discovery, we can reduce the duty cycle: e.g.
`scan_window = 30ms`, `scan_interval = 300ms` (10% duty cycle). This still
detects the PM5 within ~1-2 seconds of it waking up, while dramatically
reducing radio energy.

### 1.4 Recommendation: Always-on passive scan with low duty cycle

```
┌──────────────────────────────────────────────────────┐
│                concept2mqtt lifecycle                │
│                                                      │
│  ┌──SCANNING──┐    ┌──CONNECTED──┐    ┌──SCANNING──┐ │
│  │ passive,   │    │ telemetry,  │    │ passive,   │ │
│  │ low duty   │───→│ CSAFE cmd,  │───→│ low duty   │ │
│  │ cycle      │    │ commands    │    │ cycle      │ │
│  └────────────┘    └─────────────┘    └────────────┘ │
│      PM5 wakes →        PM5 sleeps →                 │
│      connect            disconnect detected          │
└──────────────────────────────────────────────────────┘
```

This approach:
- **Does not drain PM5 battery** (passive scan = listen only)
- **Auto-detects PM5 waking** (1-2s detection latency is fine)
- **Low Pi overhead** (10% duty cycle reduces radio energy ~90%)
- **No user action needed** to start connection

**PM5 coin cell note:** The PM5 coin cell battery powers only the clock/RTC.
The PM5's main electronics (BLE radio, LCD, processor) are powered by the
rowing machine's flywheel generator and an internal rechargeable battery. BLE
operations are powered by the rechargeable battery, not the coin cell. So even
active BLE connections while the PM5 is awake don't drain the coin cell.

---

## 2. Deep Dive: Update Rate & MQTT Latency for Coaching Apps

### 2.1 PM5 notification rates — 100ms vs 250ms vs 500ms

The PM5 supports configurable notification rates via characteristic 0x0034
(General Status Rate). The possible values:

| Setting | Rate | Msgs/sec (4 chars) | Total bytes/sec | Best for |
| --- | --- | --- | --- | --- |
| 0 | 1000ms | 4 | ~300 B/s | Smart home dashboards |
| 1 | 500ms (default) | 8 | ~600 B/s | Default balance |
| 2 | 250ms | 16 | ~1.2 KB/s | Responsive coaching |
| 3 | 100ms | 40 | ~3 KB/s | Ultra-responsive coaching |

**Analysis of 100ms vs 250ms:**

| Factor | 100ms | 250ms |
| --- | --- | --- |
| Update latency | Excellent — 100ms worst-case staleness | Good — 250ms worst-case |
| BLE radio load | High — continuous RX, little idle time | Moderate — ~60% idle time |
| Pi Zero CPU | Significant — 40 callbacks/sec + decode + MQTT publish | Manageable — 16 callbacks/sec |
| MQTT messages/sec | 40+ (one per characteristic per interval) | ~16 |
| Perceptual difference | Imperceptible vs 250ms for visual display | Smooth enough for real-time UI |
| Force plot compatibility | Marginal — tight timing budget with CSAFE interleaving | Better — more time for CSAFE round-trips |

**Recommendation:** Make this configurable (exposed as a setting), default to
**500ms** for smart home use. Coaching apps set it to **250ms** via
configuration. **100ms is overkill** — human perception of rowing metrics
(pace, distance, stroke rate) doesn't benefit from sub-250ms updates. The
display on the PM5 itself updates at ~1Hz.

The one exception is force plot data, which is inherently per-stroke
(~1/second) and doesn't benefit from faster notification rates.

### 2.2 MQTT latency analysis: concept2mqtt → broker → coaching app

The data path for a coaching app consuming MQTT data:

```
PM5 (BLE notification, ~0ms)
  → Pi Zero BLE stack (~1-5ms)
    → bleak callback (~1ms)
      → concept2mqtt decode + publish (~1-2ms)
        → MQTT broker on network (~1-10ms LAN, varies)
          → coaching app subscriber (~1ms)
            → UI render (~16ms at 60fps)
```

**End-to-end estimate: 5-35ms** (LAN), dominated by network hop and render
frame.

#### MQTT QoS impact on latency

| QoS | Handshake | Added latency | Appropriate for |
| --- | --- | --- | --- |
| 0 | Fire-and-forget | ~0ms overhead | Live telemetry (OK to miss 1 of 500) |
| 1 | PUBLISH + PUBACK | ~1-5ms LAN | State messages, workout events |
| 2 | 4-step handshake | ~5-20ms LAN | Critical commands only |

**Recommendation for live telemetry: QoS 0.**

Reasoning: live telemetry is a **continuous stream of ephemeral values**.
Missing one 250ms sample is invisible — the next one arrives 250ms later. QoS
1's PUBACK handshake adds per-message overhead that accumulates at 16 msg/sec.
QoS 0 is standard practice for high-frequency sensor data.

For **workout events** (started, ended, paused) and **commands** (sync logs,
program workout): QoS 1. These are infrequent, important, and should be
delivered reliably.

#### MQTT bus load

At 250ms with 4 characteristics, the MQTT bus load is:

- ~16 messages/sec × ~200 bytes average payload = **~3.2 KB/sec**
- With MQTT protocol overhead: ~4-5 KB/sec
- On a 100 Mbit/s LAN: **0.004% utilisation**

**Verdict: zero concern.** MQTT over LAN can handle thousands of messages/sec.
Even WiFi (Pi Zero 2 W) has ample headroom. The coaching app on Windows 11
will have no trouble keeping up.

### 2.3 Red flags for MQTT-based coaching

| Concern | Risk level | Mitigation |
| --- | --- | --- |
| Latency | **Low** — 5-35ms end-to-end on LAN | QoS 0 for live data |
| Jitter | **Low** — LAN jitter <5ms typical | Buffer 2-3 samples in coaching app |
| Missed messages | **Low** — WiFi + QoS 0 on LAN is reliable | Coaching app interpolates gaps |
| Broker failure | **Medium** — if broker goes down, all data lost | Retain not useful for live data; accept risk |
| WiFi interruption | **Medium** — Pi Zero 2 W WiFi is single-band 2.4GHz | Co-channel interference with BLE possible; separate channels recommended |
| Data ordering | **None** — single publisher, single subscriber, TCP underneath | |

**Overall assessment: MQTT via LAN is viable for coaching apps.** The total
latency budget (5-35ms) is well within the requirements for a visual coaching
display updating at 4-10 Hz. There are no red flags that would force a direct
BLE connection.

### 2.4 WiFi + BLE coexistence on Pi Zero 2 W

The Pi Zero 2 W uses a combined WiFi/BLE chip (BCM43436s). WiFi and BLE share
the 2.4GHz band with **coexistence arbitration** (the chip coordinates
internally). Practical effects:

- BLE notification delivery may occasionally be delayed by ~10-20ms during
  heavy WiFi TX (MQTT publish bursts)
- Workaround: use WiFi channel 1 or 11 (non-overlapping with BLE advertising
  channels 37/38/39)
- Real-world impact: negligible for our data rates (~5 KB/sec)

**Hardware validation needed:** Run the smoke test with simultaneous BLE
subscriptions + WiFi MQTT traffic to measure actual jitter.

---

## 3. Deep Dive: Hexagonal Architecture Options

You asked about `Pm5Port` (high-level) vs `BlePort` (low-level) as the
abstraction boundary. This is a fundamental design decision. Here are three
options with full analysis.

### Option A: High-level `Pm5Port` — PM5 as the abstraction boundary

```
┌──────────────────────────────────────────┐
│           concept2mqtt                   │
│                                          │
│  ┌──────────────────────────────┐        │
│  │  @app.device("pm5")         │        │
│  │  Device logic                │        │
│  │                              │        │
│  │  Uses: Pm5Port               │        │
│  └──────────┬───────────────────┘        │
│             │                            │
│  ┌──────────┴───────────────────┐        │
│  │  Pm5Port (Protocol)          │        │
│  │                              │        │
│  │  connect() / disconnect()    │        │
│  │  get_serial() -> str         │        │
│  │  get_firmware() -> str       │        │
│  │  subscribe_telemetry(cb)     │        │
│  │  send_csafe(cmd) -> resp     │        │
│  │  get_workout_log(n) -> Log   │        │
│  └──────────┬───────────────────┘        │
│             │                            │
│  ┌──────────┴───────────────────┐        │
│  │  BleakPm5Adapter             │        │
│  │  (bleak + CSAFE codec inside)│        │
│  └──────────────────────────────┘        │
│                                          │
│  ┌──────────────────────────────┐        │
│  │  FakePm5Adapter              │        │
│  │  (in-memory, canned data)    │        │
│  └──────────────────────────────┘        │
└──────────────────────────────────────────┘
```

**The port speaks "PM5 domain language"** — workouts, telemetry, logs. The CSAFE
framing, BLE GATT reads, byte decoding are all **inside** the adapter.

**Advantages:**

- **Device logic is clean** — reads like business requirements: "get workout
  log", "subscribe to telemetry". No byte arrays, no UUIDs, no frame checksums.
- **Test double is trivial** — `FakePm5Adapter.get_workout_log(3)` returns a
  canned `WorkoutLog` object. No BLE mocking needed at all.
- **Single adapter boundary** — one port, one adapter registration, simple
  wiring.
- **Follows Interface Segregation at the domain level** — the port represents
  exactly what the PM5 offers, nothing more.
- **CSAFE codec stays encapsulated** — it's an implementation detail of
  `BleakPm5Adapter`, not exposed to the device logic.

**Disadvantages:**

- **Large adapter surface** — `BleakPm5Adapter` is a big class doing BLE
  connection management + CSAFE framing + notification decoding + response
  parsing. Could be 500+ LOC.
- **CSAFE codec less reusable** — buried inside the adapter, harder to
  extract if another project wants just the codec (e.g., a USB transport).
- **Testing the adapter itself is harder** — to unit-test `BleakPm5Adapter`
  you'd need to mock bleak, which is awkward. Mostly tested via integration
  tests on real hardware.
- **Mixed concerns** — the adapter mixes transport (BLE), protocol (CSAFE),
  and data decoding. Violates SRP if taken strictly.

### Option B: Low-level `BlePort` — BLE as the abstraction boundary

*(This was the initial recommendation in Round 1)*

```
┌────────────────────────────────────────────┐
│           concept2mqtt                     │
│                                            │
│  ┌────────────────────────────────┐        │
│  │  @app.device("pm5")           │        │
│  │  Device logic                  │        │
│  │                                │        │
│  │  Uses: BlePort + csafe codec   │        │
│  │  + notification decoders       │        │
│  └─────┬──────────────────────────┘        │
│        │                                   │
│  ┌─────┴──────────────────────────┐        │
│  │  csafe.codec (pure module)     │        │
│  │  frame() / unframe()           │        │
│  │  No port — just functions      │        │
│  └────────────────────────────────┘        │
│                                            │
│  ┌─────┬──────────────────────────┐        │
│  │  BlePort (Protocol)            │        │
│  │                                │        │
│  │  scan() -> list[Device]        │        │
│  │  connect(addr) / disconnect()  │        │
│  │  read_char(uuid) -> bytes      │        │
│  │  write_char(uuid, data)        │        │
│  │  subscribe(uuid, callback)     │        │
│  └─────┬──────────────────────────┘        │
│        │                                   │
│  ┌─────┴──────────────────────────┐        │
│  │  BleakAdapter (bleak)          │        │
│  └────────────────────────────────┘        │
│  ┌────────────────────────────────┐        │
│  │  FakeBleAdapter (in-memory)    │        │
│  └────────────────────────────────┘        │
└────────────────────────────────────────────┘
```

**The port speaks "BLE language"** — characteristics, UUIDs, bytes. The device
logic wires CSAFE framing and notification decoding itself.

**Advantages:**

- **CSAFE codec is fully testable pure logic** — no port, no mock, just
  `assert frame(cmd) == expected_bytes`. The highest-risk code gets the best
  test coverage.
- **Adapter is thin and generic** — `BleakAdapter` is a simple bleak wrapper
  with no PM5 knowledge. Could theoretically be reused for other BLE devices.
- **Clear separation of concerns** — transport (BlePort), protocol (codec),
  domain (device logic) are cleanly layered.
- **Notification decoders are testable** — `decode_general_status(bytes)` →
  `dict`. Pure functions, no mocking.
- **CSAFE codec is reusable** — extract it as a library for USB transport
  projects, coaching apps, etc.

**Disadvantages:**

- **Device logic knows about UUIDs and bytes** — the `@app.device` coroutine
  calls `ble.write_char(CSAFE_RX_UUID, codec.frame(cmd))` and
  `codec.unframe(await ble.read_char(CSAFE_TX_UUID))`. It's lower-level.
- **Test double must simulate BLE** — `FakeBleAdapter` needs to understand
  notification callbacks, characteristic read/write semantics. More complex
  than a domain-level fake.
- **More wiring in device logic** — the device function is more complex
  because it orchestrates codec + BLE adapter + decoders.
- **PM5-specific knowledge leaks into device logic** — UUID constants, CSAFE
  command IDs, notification data formats are all referenced by the device
  function.

### Option C (Recommended): Layered — `Pm5Port` with internal CSAFE library

```
┌──────────────────────────────────────────────┐
│              concept2mqtt                    │
│                                              │
│  ┌──────────────────────────────────┐        │
│  │  @app.device("pm5")             │        │
│  │  Device logic (clean, high-level)│        │
│  │                                  │        │
│  │  Uses: Pm5Port                   │        │
│  └──────────┬───────────────────────┘        │
│             │                                │
│  ┌──────────┴───────────────────────┐        │
│  │  Pm5Port (Protocol)              │        │
│  │  High-level PM5 operations       │        │
│  └──────────┬───────────────────────┘        │
│             │                                │
│  ┌──────────┴───────────────────────┐        │
│  │  BleakPm5Adapter                 │        │
│  │  ├── uses: csafe.codec (library) │        │
│  │  ├── uses: decoders (library)    │        │
│  │  └── uses: bleak (transport)     │        │
│  └──────────────────────────────────┘        │
│                                              │
│  ┌──────────────────────────────────┐        │
│  │  csafe/                          │        │
│  │  ├── codec.py   (frame/unframe)  │        │
│  │  ├── commands.py (cmd builders)  │        │
│  │  └── decoders.py (notification   │        │
│  │       parse + response decode)   │        │
│  │                                  │        │
│  │  Pure library — no I/O, no port  │        │
│  │  100% unit-testable              │        │
│  └──────────────────────────────────┘        │
│                                              │
│  ┌──────────────────────────────────┐        │
│  │  FakePm5Adapter                  │        │
│  │  (canned domain-level responses) │        │
│  └──────────────────────────────────┘        │
└──────────────────────────────────────────────┘
```

**This is a hybrid:** The port speaks PM5 domain language (like Option A), but
the CSAFE codec and notification decoders are extracted as **standalone pure
libraries** (like Option B's key advantage).

**Why this is the best of both worlds:**

| Property | Option A | Option B | **Option C** |
| --- | --- | --- | --- |
| Device logic cleanliness | Excellent | Fair | **Excellent** |
| CSAFE codec testability | Poor (buried) | Excellent | **Excellent** |
| Adapter complexity | High (monolith) | Low (thin) | **Medium (uses libraries)** |
| Test double simplicity | Excellent | Fair | **Excellent** |
| CSAFE codec reusability | Poor | Excellent | **Excellent** |
| Notification decoder testing | Embedded | Excellent | **Excellent** |
| PM5 knowledge in device logic | None | Leaks in | **None** |
| Adapter testability | Hard | Easy | **Medium (integration)** |

**The crucial insight:** The CSAFE codec is not domain logic — you're right to
question that. It's protocol encoding, which is indeed closer to
infrastructure. But it's **pure, deterministic, byte-level logic** that is
highly testable and highly reusable. It deserves to be a well-tested library
module that the adapter *uses*, not a part of the adapter's private
implementation.

The port (`Pm5Port`) is the seam where we swap real hardware for
test doubles. The codec library is tested directly, not through the port boundary.

### 3.1 What the Pm5Port Protocol might look like

```python
@runtime_checkable
class Pm5Port(Protocol):
    """High-level PM5 operations over BLE + CSAFE."""

    # Connection lifecycle
    async def scan(self, timeout: float = 10.0) -> list[Pm5Device]: ...
    async def connect(self, device: Pm5Device) -> None: ...
    async def disconnect(self) -> None: ...
    @property
    def is_connected(self) -> bool: ...

    # Device identity (GATT reads)
    async def get_device_info(self) -> DeviceInfo: ...

    # Telemetry (BLE notifications)
    async def subscribe_general_status(self, callback: GeneralStatusCallback) -> None: ...
    async def subscribe_additional_status(self, callback: AdditionalStatusCallback) -> None: ...
    async def subscribe_stroke_data(self, callback: StrokeDataCallback) -> None: ...
    async def unsubscribe_all(self) -> None: ...

    # CSAFE operations (request-response over BLE)
    async def get_workout_state(self) -> WorkoutState: ...
    async def get_workout_log(self, entry: int) -> WorkoutLogEntry: ...
    async def get_force_plot_data(self) -> list[int]: ...
    async def set_datetime(self, dt: datetime) -> None: ...
    async def program_workout(self, config: WorkoutConfig) -> None: ...
```

This keeps the port **domain-focused** while all the BLE+CSAFE complexity
lives in `BleakPm5Adapter` backed by the `csafe` library.

### 3.2 What the CSAFE library looks like

```python
# csafe/codec.py — pure functions, no I/O
def frame_command(commands: list[CsafeCommand]) -> bytes: ...
def unframe_response(data: bytes) -> CsafeResponse: ...
def compute_checksum(data: bytes) -> int: ...
def stuff_bytes(data: bytes) -> bytes: ...
def unstuff_bytes(data: bytes) -> bytes: ...

# csafe/commands.py — command builders
def get_status() -> CsafeCommand: ...
def get_workout_log(entry: int) -> CsafeCommand: ...
def set_datetime(dt: datetime) -> CsafeCommand: ...

# csafe/decoders.py — BLE notification parsers
def decode_general_status(data: bytes) -> GeneralStatus: ...
def decode_additional_status_1(data: bytes) -> AdditionalStatus1: ...
def decode_stroke_data(data: bytes) -> StrokeData: ...
```

All pure functions. All testable with `assert decode_general_status(b'\x01\x02...') == GeneralStatus(...)`. The YAML spec is the **test oracle** — we can generate test vectors from it.

### 3.3 Decision needed

My recommendation is **Option C**. The key question for you:

> Does separating the CSAFE codec as a library module (testable, reusable, but
> not behind a port boundary) feel right? Or does the cleaner single-port
> approach of Option A appeal despite burying the codec?

---

## 4. Deep Dive: PM5 Dual BLE Connections & Coaching App Architecture

### 4.1 Can the PM5 support two simultaneous BLE connections?

BLE 4.2 peripherals can theoretically support multiple simultaneous central
connections if their firmware implements it. However:

**PM5 limitations (based on spec and observed behaviour):**

- The Concept2 CSAFE spec does not document multi-connection support
- The PM5 GATT table includes a single PM Control Service with one RX/TX
  characteristic pair — this implies a single CSAFE command channel
- The nRF52 chipset (PM5's BLE chip) supports up to 20 simultaneous
  connections in firmware, but Concept2's firmware may limit this to 1
- **ErgData (Concept2's official app) appears to be the sole BLE
  connection** — when ErgData is connected, other apps cannot connect

**Practical conclusion: the PM5 very likely supports only 1 BLE connection
at a time.** Even if the hardware supports more, Concept2's firmware almost
certainly doesn't expose multiple CSAFE channels.

### 4.2 What this means for the coaching app

If only one BLE connection is possible, the coaching app on Windows 11
**cannot connect to the PM5 directly** while concept2mqtt is connected. This
makes the MQTT relay model **the only option** for simultaneous smart home +
coaching use.

This actually strengthens the case for concept2mqtt as a central data bridge:

```
PM5  ──BLE──→  concept2mqtt (Pi)  ──MQTT──→  Home Assistant
                     │                        coaching app
                     │                        concept2stats
                     └──MQTT──→  (any number of subscribers)
```

One BLE connection, many MQTT consumers. concept2mqtt is the **single point of
access** to the PM5.

### 4.3 Alternative: coaching app connects directly instead

If we abandon the MQTT relay model for coaching, the coaching app would need
its own BLE connection to the PM5. This means:

| Scenario | PM5 BLE connection | Who gets data |
| --- | --- | --- |
| Smart home only | concept2mqtt (Pi) | Home Assistant |
| Coaching only | coaching app (Windows) | Coaching app |
| Both simultaneously | **Not possible** (1 BLE conn) | Must time-share or use MQTT |

**Time-sharing is fragile** — concept2mqtt disconnects when the coaching app
wants the PM5, and reconnects when coaching is done. This requires coordination
and may miss workout data if the handoff is imperfect.

### 4.4 Validation needed

We should validate the single-connection hypothesis on real hardware:

```
Test script (for Pi demo project):
1. Connect to PM5 via bleak from device A
2. While connected, attempt connection from device B
3. Observe: does device B's connection succeed? Does device A get dropped?
4. If dual-connection works: can both read notifications simultaneously?
   Can both send CSAFE commands?
```

This test should be added to the demo project's validation scripts.

### 4.5 Recommendation

**Design concept2mqtt as the sole BLE gateway.** The coaching app on Windows 11
consumes MQTT data from concept2mqtt. If the PM5 allows only one BLE
connection (very likely), this is the only architecture that supports
concurrent smart home + coaching.

The CSAFE codec library should still be designed as reusable (§3, Option C) so
that IF the coaching app ever needs a direct BLE connection (standalone mode,
no concept2mqtt), it can import the same codec.

---

## 5. Revised Feature Set

Incorporating all decisions from above:

### 5.1 MVP

| # | Feature | Notes |
| --- | --- | --- |
| F1 | **PM5 discovery & BLE connection** | Always-on passive scan, auto-connect, reconnection |
| F2 | **Device identity** | Serial, FW, HW, machine type — published on connect |
| F3 | **Live workout telemetry** | All notification characteristics, configurable rate (default 500ms) |
| F4 | **Workout lifecycle events** | Start/end/pause/resume detection from state machine |
| F5 | **Health & availability** | cosalette health reporting for PM5 online/offline |
| F6 | **CSAFE codec library** | Pure module: frame/unframe, command builders, decoders |
| F7 | **Configurable notification rate** | Setting to control 100ms/250ms/500ms/1000ms |

### 5.2 Fast-follow (immediately after MVP)

| # | Feature | Notes |
| --- | --- | --- |
| F8 | **Full log history dump** | On-demand via MQTT command, for initial smart home setup |
| F9 | **Post-workout log retrieval** | Auto-trigger after workout end |
| F10 | **Date/time sync** | Set PM5 clock on each connection |

### 5.3 Extended (planned)

| # | Feature | Notes |
| --- | --- | --- |
| F11 | **Force plot data** | Opt-in, CSAFE polling per stroke, for coaching apps |
| F12 | **Workout programming** | Bidirectional: accept config via MQTT, program PM5 |
| F13 | **Heart rate passthrough** | Relay HR from PM5's ANT+ paired monitor |
| F14 | **HA MQTT Discovery** | Monitor cosalette framework readiness, early-adopter feedback |
| F15 | **Error log retrieval** | On-demand diagnostics |

### 5.4 Separate projects (enabled by concept2mqtt)

| Project | Depends on | Description |
| --- | --- | --- |
| concept2coach | F3, F4, F7, F11 | Real-time coaching app on Windows 11, MQTT-driven |
| concept2stats | F8, F9, F4 | Historical analysis, database persistence |
| concept2logbook | — | Concept2 online logbook API integration |
| HA integration | F14, all topics | Home Assistant entities and automations |

---

## 6. Revised MQTT Topic Layout

```
concept2mqtt/                          # app prefix
├── status                             # app heartbeat / LWT
├── error                              # global error events
└── pm5/                               # device segment
    ├── state                          # aggregated live telemetry (JSON)
    ├── availability                   # "online" / "offline" (cosalette managed)
    ├── error                          # device-scoped error events
    ├── set                            # inbound commands (sync, program, etc.)
    ├── identity/state                 # device info (serial, FW, HW, machine type)
    ├── workout/state                  # lifecycle events (started, ended, paused)
    ├── stroke/state                   # per-stroke metrics
    ├── force_plot/state               # force curve data (opt-in)
    └── log/                           # workout log entries
        └── {entry_index}/state        # individual log entry
```

**QoS mapping:**

| Topic pattern | QoS | Rationale |
| --- | --- | --- |
| `pm5/state` | 0 | High-frequency telemetry, ephemeral |
| `pm5/stroke/state` | 0 | Per-stroke, ephemeral |
| `pm5/force_plot/state` | 0 | Per-stroke, ephemeral |
| `pm5/workout/state` | 1 | Important lifecycle events, infrequent |
| `pm5/identity/state` | 1 | Published once on connect, retained |
| `pm5/log/*/state` | 1 | Workout logs, important data |
| `pm5/set` | 1 | Inbound commands, must be delivered |
| `pm5/availability` | 1 | Cosalette standard, retained |
| `status` | 1 | LWT / heartbeat, retained |

---

## 7. Remaining Open Questions (Round 2)

Most Round 1 questions are resolved. These remain:

### 7.1 Architecture

**Q-A1. Option C confirmation** — Does the layered approach (§3, Option C:
`Pm5Port` + CSAFE library) work for you?

**Q-A2. Topic layout confirmation** — Does the proposed topic tree (§6) look
right? Specifically: is `pm5/state` vs `pm5/stroke/state` vs
`pm5/force_plot/state` the right granularity, or do you want different
groupings?

### 7.2 Hardware Validation

**Q-H1. BLE dual connection test** — We should validate that PM5 supports only
1 BLE connection. This needs a test script for the demo project. Should I
draft it?

**Q-H2. Notification rate test** — We should measure actual notification
delivery timing at 250ms on the Pi Zero 2 W with WiFi active. Draft test?

**Q-H3. BLE reconnection test** — How quickly does the PM5 start re-advertising
after a user wakes it? Test for scan-to-connect latency.

### 7.3 Coaching App Scoping

**Q-C1. Coaching app as MQTT consumer confirmed?** — Based on the analysis in
§4, the coaching app on Windows 11 will consume MQTT data from concept2mqtt
rather than connecting to the PM5 directly. Agreed?

**Q-C2. Force plot data via MQTT** — For the coaching app, force plot data
arrives as individual CSAFE responses (~16 data points per request). Should
concept2mqtt assemble full stroke curves before publishing, or publish raw
chunks and let the coaching app assemble?

---

## 8. Hardware Validation Scripts Needed

These scripts should be prepared for the demo project on the Pi:

| # | Script | Purpose |
| --- | --- | --- |
| V1 | `test_dual_ble.py` | Attempt 2 simultaneous BLE connections to PM5 |
| V2 | `test_notification_rates.py` | Subscribe at 250ms/100ms, measure actual delivery jitter |
| V3 | `test_all_characteristics.py` | Subscribe to all 6+ notification chars simultaneously |
| V4 | `test_csafe_roundtrip.py` | Measure CSAFE command latency (send + receive) |
| V5 | `test_reconnection.py` | Disconnect, wait, measure time to re-discover + reconnect |
| V6 | `test_wifi_ble_coexistence.py` | BLE notifications + WiFi MQTT publish, measure jitter |
| V7 | `test_force_plot.py` | Poll force plot data during workout, measure completeness |

These can be drafted as part of the planning phase and handed to the demo
project.

---

## 9. References & Resources

### Existing PM5 open-source projects

- **pROWess** — Python PM5 BLE library. Cross-referenced in CSAFE spec. Source
  of validation for frameCSAFE/unframeCSAFE and notification decoding.
- **c2bluetooth** (Dart) — Flutter PM5 BLE library. Validates enum values and
  BLE UUID usage.
- **py-concept2** / **pyrow** — Python PM5 USB libraries. Same CSAFE protocol,
  USB transport. Useful for codec validation.
- **ErgData** — Concept2's official iOS/Android app. Baseline for feature parity.
- **CrewNerd** — Third-party rowing app. Reference for coaching UX.

### BLE on Pi Zero 2 W

- BCM43436s chip — BLE 4.2 (matches PM5)
- `bleak` 0.22+ with `dbus-fast` for Linux/BlueZ
- BlueZ 5.66+ recommended for stability
- `bluetoothctl` for manual debugging

### CSAFE protocol constraints

- Max frame: 120 bytes (incl. overhead)
- Min inter-frame gap: 50ms → max ~20 CSAFE commands/sec
- BLE characteristic: 20 bytes default → large frames segmented
- ATT MTU negotiation can increase to 512 bytes (PM5 V168.050+)
- No frame-level ACK/NAK — errors = missing/malformed responses
- Multiple commands packable into single frame (saves round-trips)

---

## Round 3 — Decisions & Elaborations

### Status of Round 2 Decisions

| Topic | Decision | Notes |
| --- | --- | --- |
| Architecture (Q-A1) | **Option C confirmed** | Pm5Port + CSAFE codec as standalone library |
| Coaching app (Q-C1) | **Separate project** | MQTT consumer; connectivity demands noted |
| Force plot assembly (Q-C2) | **Assemble before publishing** | concept2mqtt publishes complete stroke curves |
| CSAFE codec language | **Rust (PyO3/maturin)** | Learning opportunity; elaboration in §10 |
| Dual-connection test | **PoC planned** | Validate PM5 + iPhone Concept2 app coexistence; §11 |

---

## 10. Deep Dive: CSAFE Codec in Rust

### 10.1 Why Rust for the CSAFE codec?

The CSAFE codec is pure, deterministic, byte-level logic — no I/O, no async,
no complex state. This is the **simplest subset of Rust**: byte slices, Vec,
enums, structs, pattern matching. No lifetimes, no async, no complex generics.

The case for Rust here is **not primarily performance** (Python is fast enough
at ~10 frames/sec on a Pi). The case is:

| Factor | Pure Python | Rust + PyO3 |
| --- | --- | --- |
| **Correctness guarantees** | Runtime errors for byte-level bugs | Compile-time catch via type system |
| **Reusability** | Python-only consumers | Any language via C FFI, Wasm, or native Rust |
| **Testability** | Good (`pytest`) | Excellent (`cargo test` — sub-millisecond runs) |
| **Learning value** | None (you know Python) | Significant (new language, new paradigm) |
| **Ecosystem play** | Limited | Publish crate for USB transport, other projects |
| **Performance** | ~5-15µs per frame (sufficient) | ~0.1-0.5µs per frame (100x faster, not needed) |
| **PyO3 call overhead** | N/A | ~50-200ns per call (negligible at <100 calls/sec) |

**Bottom line:** Performance isn't the driver. Correctness, reusability, and
learning are. This is an ideal "first Rust project" — well-scoped, no I/O
complexity, pure logic with a rich test oracle (the YAML spec).

### 10.2 Mono-repo: Can Rust and Python coexist?

**Yes.** This is production-proven at scale. Notable projects with the same
pattern: `pydantic-core`, `polars`, `ruff`, `cryptography`, `tiktoken`,
`tokenizers`. All are Rust libs exposed to Python via PyO3 + maturin.

**Proposed directory structure:**

```
concept2mqtt/
├── Cargo.toml                         # Rust workspace root
├── pyproject.toml                     # Python workspace root (uv)
├── Taskfile.yml
├── packages/
│   ├── csafe-codec/                   # Rust crate
│   │   ├── Cargo.toml
│   │   ├── pyproject.toml             # maturin build config
│   │   ├── src/
│   │   │   ├── lib.rs                 # Rust library (pure logic)
│   │   │   ├── codec.rs              # Frame/unframe
│   │   │   ├── commands.rs           # Command builders
│   │   │   └── decoders.rs           # Notification parsers
│   │   ├── python/
│   │   │   └── csafe_codec/          # Python re-exports + types
│   │   │       ├── __init__.py
│   │   │       └── py.typed
│   │   └── tests/                    # Rust unit tests
│   │       └── test_vectors.rs       # Generated from YAML spec
│   ├── src/
│   │   └── concept2mqtt/             # Python app (unchanged)
│   └── tests/                        # Python tests
├── docs/
└── .devcontainer/
```

**uv workspace integration:**

```toml
# Root pyproject.toml additions
[tool.uv.workspace]
members = ["packages/csafe-codec", "packages/src"]

[tool.uv.sources]
csafe-codec = { workspace = true }
```

```toml
# packages/csafe-codec/pyproject.toml
[project]
name = "csafe-codec"
version = "0.1.0"
requires-python = ">=3.13"

[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[tool.maturin]
python-source = "python"
module-name = "csafe_codec._native"
features = ["pyo3/extension-module"]
```

The Python app declares `csafe-codec` as a dependency; `uv sync` builds it
automatically via maturin as the PEP 517 build backend.

### 10.3 Dev container adjustments

**Current:** Python dev container (Debian Trixie, Python 3.13.5, uv).

**To add:**

```json
// .devcontainer/devcontainer.json — add to features
{
  "features": {
    "ghcr.io/devcontainers/features/rust:1": {
      "version": "latest",
      "profile": "default"
    }
  }
}
```

This installs `rustup`, `cargo`, `rustc`, `rust-analyzer` (for IDE support).
Additionally needed:

- `maturin` — install via `uv tool install maturin` (reuse existing uv)
- Optional: `sccache` for build caching across rebuilds
- `.cargo/config.toml` for workspace linker settings (PyO3 + Cargo workspace gotcha)

**Disk impact:** ~1-2 GB for Rust toolchain + build artifacts.
**Rebuild time:** +30-60s on dev container rebuild (one-time).

### 10.4 Development workflow

| Task | Command |
| --- | --- |
| Rust unit tests | `cargo test -p csafe-codec` |
| Build + install into venv | `maturin develop --uv` (from `packages/csafe-codec/`) |
| Python integration tests | `task test:unit` (after `maturin develop`) |
| Optimised build | `maturin develop --uv -r` |
| Cross-compile for Pi | `maturin build --release --target aarch64-unknown-linux-gnu --zig` |

**Iteration speed:** `cargo test` runs in <1 second. `maturin develop` takes
3-10 seconds (first) or 1-3 seconds (incremental). This is faster than
equivalent Python test cycles for byte-level logic because `cargo test`
doesn't need a Python interpreter.

New Taskfile entries needed:

```yaml
csafe:test:
  desc: Run Rust unit tests for CSAFE codec
  cmds:
    - cargo test -p csafe-codec

csafe:build:
  desc: Build CSAFE codec and install into venv
  cmds:
    - cd packages/csafe-codec && maturin develop --uv

csafe:build-pi:
  desc: Cross-compile CSAFE codec for Pi (aarch64)
  cmds:
    - cd packages/csafe-codec && maturin build --release --target aarch64-unknown-linux-gnu --zig
```

### 10.5 How the Python project gets the library

**During development (dev container):**

```
uv sync
# → resolves csafe-codec as workspace member
# → calls maturin (PEP 517 build backend) to compile Rust → .so
# → installs .so into .venv/lib/python3.13/site-packages/csafe_codec/
```

Or explicitly: `maturin develop --uv` inside `packages/csafe-codec/`.

Then in Python:

```python
from csafe_codec import frame_command, unframe_response, decode_general_status
```

**For deployment to Pi:**

Three options, in order of recommendation:

| Method | How | Pros | Cons |
| --- | --- | --- | --- |
| **CI-built wheel** | `maturin-action` in GitHub Actions builds aarch64 wheel → attached to release | No Rust needed on Pi, reproducible | Requires CI setup |
| **Cross-compile locally** | `maturin build --release --target aarch64-unknown-linux-gnu --zig` → copy .whl to Pi | Quick, no CI needed | Manual step |
| **Build on Pi** | Install Rust on Pi, `maturin build` | Full self-contained | Slow (~5-30 min), 512MB RAM is tight |

**Recommended:** CI-built wheel. The Pi only ever runs `pip install csafe_codec-*.whl`.

```yaml
# .github/workflows/build.yml (simplified)
jobs:
  build-wheel:
    strategy:
      matrix:
        target:
          - { triple: x86_64-unknown-linux-gnu, manylinux: "2_28" }
          - { triple: aarch64-unknown-linux-gnu, manylinux: "2_28" }
    steps:
      - uses: actions/checkout@v4
      - uses: PyO3/maturin-action@v1
        with:
          target: ${{ matrix.target.triple }}
          manylinux: ${{ matrix.target.manylinux }}
          args: --release --locked
          working-directory: packages/csafe-codec
      - uses: actions/upload-artifact@v4
        with:
          name: wheel-${{ matrix.target.triple }}
          path: target/wheels/*.whl
```

The wheel artifact looks like:

```
csafe_codec-0.1.0-cp313-cp313-manylinux_2_28_aarch64.whl
```

Inside: a compiled `.so` (~200KB-1MB) + Python wrapper. Standard `pip install`.

### 10.6 Rust beginner guidance — what to expect

**What you'll use (simple Rust):**
- `&[u8]` (byte slices), `Vec<u8>` (byte vectors)
- `enum` and `struct` for data types
- Pattern matching (`match`) for parsing state machines
- `Result<T, E>` for error handling
- `#[test]` for unit tests

**What you won't need (complex Rust):**
- No `async`/`await` (the codec is pure, synchronous logic)
- No explicit lifetimes (PyO3 handles the Python↔Rust boundary)
- No complex generics or trait bounds
- No `unsafe` code
- No concurrency primitives

**Learning path:**
1. Rust Book chapters 1-6 (basics, ownership, structs, enums) — 1-2 days
2. PyO3 user guide (functions, classes, type conversions) — 1 day
3. Implement `stuff_bytes` + `checksum` as first functions — 1 evening
4. Build from there: frame/unframe, then command builders, then decoders

**IDE support:** `rust-analyzer` in VS Code provides autocomplete, inline
type hints, error highlighting, and refactoring tools. It's comparable to
Python's `pylance` in quality.

### 10.7 When to introduce Rust

**Decision: Rust from day one.** *(Updated Round 3 — user chose Rust-first
for the learning opportunity.)*

The CSAFE codec will be written in Rust from the start, with a focus on
learning idiomatic Rust and the Rust ecosystem. This is viable because:

- The codec is **pure logic** — no async, no I/O, no lifetimes complexity
- The YAML spec provides a **complete test oracle** for test-driven development
- **PyO3 bindings** let us test from Python immediately (`maturin develop`)
- The architecture (Option C) isolates the codec — concept2mqtt's Python code
  only sees the import boundary, never raw Rust types

**Development order:**

1. **Rust codec crate** — frame/unframe, checksum, byte stuffing. TDD with
   `cargo test` using test vectors from the YAML spec.
2. **PyO3 bindings** — expose codec functions to Python. `maturin develop`
   installs into the venv.
3. **BleakPm5Adapter** (Python) — uses the Rust codec via Python imports.
   Validates on real PM5 hardware.
4. **Publish** — `cargo publish` to crates.io, `maturin publish` to PyPI.

**Validation against hardware** happens at the adapter level (Python) — not
in the codec itself. The codec consumes and produces `bytes`; the adapter
passes bytes between bleak and the codec. If a spec interpretation is wrong,
we fix the Rust codec and re-run `cargo test` + `maturin develop`.

### 10.8 Publication plan

**crates.io:** Primary target. The `csafe-codec` crate will be a standalone
Rust library usable by any Rust project (USB transport, Wasm coaching apps,
embedded systems, etc.).

**PyPI:** Secondary target via maturin. The `csafe-codec` Python package wraps
the Rust crate. Published alongside the crate for Python consumers.

**Naming implications:**
- Crate name: `csafe-codec` (Rust convention: kebab-case)
- Python package name: `csafe-codec` (PyPI) / `csafe_codec` (import)
- Public API must be thoughtfully designed from the start — breaking changes
  after publication are costly
- Documentation: `///` doc comments in Rust (rendered by docs.rs) +
  Python docstrings in the PyO3 bindings
- License: same as concept2mqtt (MIT or Apache-2.0, TBD)

---

## 11. Proof of Concept: PM5 Dual BLE Connection Test

### 11.1 Purpose

Validate whether the PM5 can maintain **two simultaneous BLE connections**:
one from a Pi (concept2mqtt) and one from an iPhone (Concept2 app / ErgData).

This directly answers the critical architecture question from §4: is
concept2mqtt the sole BLE gateway, or can other apps connect simultaneously?

### 11.2 Test matrix

| # | Scenario | Device A (Pi) | Device B (iPhone) | What to observe |
| --- | --- | --- |  --- | --- |
| T1 | Pi connects first | BLE connected, reading notifications | Attempt connect via Concept2 app | Does iPhone connect? Does Pi get dropped? |
| T2 | iPhone connects first | Concept2 app connected | Attempt `bleak` connect from Pi | Does Pi connect? Does iPhone get dropped? |
| T3 | Simultaneous notifications | Both connected (if T1/T2 succeed) | Both subscribed to rowing status | Do both receive notifications? Same timing? |
| T4 | CSAFE coexistence | CSAFE command from Pi | Concept2 app active | Does CSAFE interfere with each other? |

### 11.3 Test script — `test_dual_ble.py`

This script runs on the Pi. The iPhone simply has the Concept2 app open and
connected. The test observes what happens from the Pi's perspective.

**Script outline:**

```python
"""PM5 dual BLE connection proof-of-concept.

Validates whether the PM5 can maintain two simultaneous BLE connections.
Run this on the Pi while the Concept2 app is connected on an iPhone.

Scenarios:
  1. Pi connects while iPhone is already connected
  2. Pi reads device info (GATT read) with both connected
  3. Pi subscribes to notifications with both connected
  4. Pi disconnects; iPhone should remain connected (verify manually)

Prerequisites:
  - PM5 powered on (rowing or connected menu)
  - iPhone Concept2 app connected to PM5
  - Pi in BLE range of PM5

Run: uv run python docs/planning/legacy/examples/test_dual_ble.py
"""

import asyncio
import logging
from bleak import BleakClient, BleakScanner

# PM5 UUIDs (same as smoke_ble.py)
UUID_SERIAL = "ce060012-43e5-11e4-916c-0800200c9a66"
UUID_ROWING_GENERAL = "ce060031-43e5-11e4-916c-0800200c9a66"
PM5_PREFIX = "PM5"

log = logging.getLogger("dual_ble")

async def test_dual_connection():
    results = {}

    # Phase 1: Scan (should see PM5 even if iPhone is connected)
    log.info("Phase 1: Scanning for PM5...")
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
    pm5 = next(
        (d for d, _ in devices.values() if d.name and PM5_PREFIX in d.name),
        None,
    )
    if not pm5:
        log.error("PM5 not found — is it on? Is iPhone connected?")
        results["scan"] = "FAIL — PM5 not advertising"
        # Key finding: if PM5 not advertising, iPhone has exclusive connection
        return results

    results["scan"] = f"PASS — found {pm5.name} ({pm5.address})"
    log.info("  Found: %s", pm5.name)

    # Phase 2: Connect (the critical test)
    log.info("Phase 2: Attempting BLE connection...")
    try:
        async with BleakClient(pm5, timeout=20.0) as client:
            results["connect"] = f"PASS — dual connection works!"
            log.info("  Connected! Dual BLE connection is possible.")

            # Phase 3: Read device info
            log.info("Phase 3: Reading device info...")
            try:
                serial = await client.read_gatt_char(UUID_SERIAL)
                results["gatt_read"] = f"PASS — serial: {serial.decode()}"
            except Exception as e:
                results["gatt_read"] = f"FAIL — {e}"

            # Phase 4: Subscribe to notifications
            log.info("Phase 4: Subscribing to notifications (10s)...")
            received = []
            def on_notify(_, data):
                received.append(data)
                log.info("  Notification #%d: %d bytes", len(received), len(data))

            await client.start_notify(UUID_ROWING_GENERAL, on_notify)
            await asyncio.sleep(10.0)
            await client.stop_notify(UUID_ROWING_GENERAL)
            results["notifications"] = f"PASS — {len(received)} received"

            # Phase 5: Manual check prompt
            log.info("Phase 5: Check iPhone — is Concept2 app still connected?")
            input("  Press Enter after checking iPhone status...")

        results["disconnect"] = "PASS — clean disconnect"

    except Exception as e:
        results["connect"] = f"FAIL — {e}"
        log.error("  Connection failed: %s", e)
        log.info("  This likely means PM5 supports only 1 BLE connection.")

    # Summary
    print("\n" + "=" * 60)
    print("DUAL BLE CONNECTION TEST RESULTS")
    print("=" * 60)
    for k, v in results.items():
        marker = "✓" if "PASS" in v else "✗"
        print(f"  {marker} {k:20s} {v}")
    print("=" * 60)

    return results
```

### 11.4 Expected outcomes

**Most likely outcome (single connection only):**
- T1: Pi connects → iPhone gets disconnected (or vice versa)
- Scan may still see PM5 advertising even with iPhone connected (advertising
  ≠ exclusive connection), but connection attempt fails or drops the other

**Possible outcome (dual connection works):**
- Both devices connect successfully
- Both can read GATT characteristics
- Notification delivery to both (may have jitter)
- CSAFE commands may conflict (single RX/TX channel)

**Either outcome is useful:**
- Single connection → concept2mqtt is the sole gateway (architecture confirmed)
- Dual connection → more flexible, but concept2mqtt should still be the
  primary data source for MQTT consumers

### 11.5 What about alternative validation approaches?

Instead of the iPhone Concept2 app, we could use a second Pi or a laptop with
bleak. But using the **actual Concept2 app on an iPhone** is the most realistic
test because:

1. It's what users actually do (row with ErgData/Concept2 app)
2. It tests the exact firmware behaviour Concept2 implemented
3. It's the scenario we need to support (concept2mqtt + user's phone app)

### 11.6 Logistics

- **Hardware needed:** Pi Zero 2 W + iPhone + PM5
- **Prerequisites:** bleak installed on Pi (`uv pip install bleak`)
- **PM5 state:** Must be on and in a state where it accepts connections
  (just-woken or in workout)
- **Time estimate:** 15 minutes hands-on
- **When to run:** Before starting MVP development — this is a go/no-go
  for the single-gateway architecture

---

## 12. Status of Round 3 Decisions

| Topic | Decision | Notes |
| --- | --- | --- |
| Topic layout (Q-A2) | **Confirmed** | §6 layout approved — covers all features, cosalette-compatible, bidirectional |
| Rust timing (Q-R1) | **Rust from day one** | Focus on learning Rust ecosystem + idiomatic approaches; §10.7 updated |
| crates.io publication (Q-R2) | **Yes — crates.io + PyPI** | Publish as standalone; mono-repo development; §10.8 added |
| PoC script (Q-P1) | **Drafted** | `test_dual_ble.py` added to legacy examples |

---

## 13. Sparring Complete — Ready for Planning

All major design questions are resolved. The sparring phase has produced:

1. **Architecture:** Option C — `Pm5Port` protocol + standalone CSAFE codec (Rust)
2. **CSAFE codec:** Rust-first via PyO3/maturin, mono-repo, published to crates.io + PyPI
3. **MQTT design:** Topic layout confirmed, QoS mapping defined
4. **BLE strategy:** Always-on passive scan, sole gateway model
5. **Feature tiers:** MVP (F1-F7) → fast-follow (F8-F10) → extended (F11-F15)
6. **PoC:** Dual BLE connection test script ready for hardware validation

**Next step:** Move from sparring to detailed work planning. Create beads
epics and tasks, define acceptance criteria, establish the implementation
order. The PoC (dual BLE test) should run first — it's a go/no-go gate for
the single-gateway architecture.
