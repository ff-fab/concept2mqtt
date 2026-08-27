# PM5 BLE Relay — Hardware Validation Procedure

Manual test procedure for `c2m-ooz.3` (BLE peripheral relay). Everything here
needs physical hardware and therefore cannot be executed in CI or by an agent.
The automated unit tests cover the relay logic only; this document covers the
acceptance criteria that unit tests structurally cannot reach.

**Context:** [ADR-003 — BLE Gateway Architecture](../adr/ADR-003-ble-gateway-architecture.md)

---

## 1. Hardware and environment

| Item                | Requirement                                                  |
| ------------------- | ------------------------------------------------------------ |
| Host                | Raspberry Pi running the project image                       |
| Kernel              | `>= 6.18.42-v8+` (past the raspberrypi/linux#7473 regression) |
| Adapter `hci0`      | Onboard controller — **central** role, holds the real PM5    |
| Adapter `hci1`      | CSR8510-class USB dongle — **peripheral** role               |
| Erg                 | Concept2 with PM5, firmware version recorded below           |
| Phone               | iPhone with the official Concept2 app installed              |
| Capture host        | Mac with Xcode + the Additional Tools "PacketLogger"         |

Pre-flight:

```bash
uname -r                       # must be >= 6.18.42-v8+
hciconfig -a                   # hci0 and hci1 both present
bluetoothctl power on
```

Wake the PM5 by pulling the handle. Make sure **no** other device (phone,
watch, previous session) is holding a connection to it — the PM5 accepts only
one, and this is the single most common cause of a failed run.

---

## 2. Step A — Traffic capture (blocking, do this first)

**Criterion:** confirms which GATT service the official app actually queries —
the proprietary CSAFE family (`ce06xxxx`) or the standard Fitness Machine
Service (`0x1826`). Building the emulated server against the wrong service
means the app will not recognise the relay as a PM5 at all, so resolve this
before trusting any later step.

1. On the Mac: install the Additional Tools for Xcode, then enable the iPhone's
   Bluetooth logging profile (Settings → Privacy → Analytics, after installing
   the Bluetooth logging configuration profile from Apple's developer
   downloads). Reboot the phone.
2. Launch PacketLogger, choose the connected iPhone as the capture source and
   start recording.
3. On the phone, open the Concept2 app and connect **directly to the real PM5**
   (relay off). Row a short piece. Use start, pause and stop. Visit every
   live-session screen.
4. Stop the capture and export it (`.pklg`).
5. In the capture, filter for `ATT` and inspect the first
   `Read By Group Type Response` after connection, then every subsequent
   `Write Request` / `Handle Value Notification`. Record which base UUID they
   target.

Record the answer here:

- [ ] App uses the **proprietary** `ce06xxxx` services → keep the default
      `pm5-proprietary` profile.
- [ ] App uses **FTMS** `0x1826` → run the relay with `--profile ftms` and
      extend `_FTMS_SERVICES` in `packages/concept2mqtt/src/concept2mqtt/ble/profile.py`
      from the capture (the FTMS table is currently marked UNVERIFIED).
- [ ] App uses **both** → note which characteristics come from which service;
      the profile registry can hold a combined profile.

Attach or link the `.pklg` (or a written summary of the service/characteristic
list) to `c2m-ooz.3` before closing it.

---

## 3. Step B — Bring up the relay

```bash
uv run --with bleak --with bluez-peripheral \
    python docs/planning/legacy/examples/relay_pm5.py \
    --central hci0 --peripheral hci1 --profile pm5-proprietary
```

Expected log sequence:

1. `Scanning for a PM5 on hci0` → `Found PM5 ... connecting`
2. `BLE relay started: profile=pm5-proprietary services=5 streaming=N/M`
3. `Advertising 'PM5 <serial> Row' on hci1`
4. `Relay live. Connect the Concept2 app to the advertised PM5.`

If `streaming=N/M` shows `N < M`, the connected firmware does not implement
every characteristic in the spec table. That is tolerated by design — note the
warned UUIDs, they are candidates for the known-gap list in Step D.

Every 10 s the script logs `RelayStats(...)`. Use those counters as the
objective evidence for the criteria below.

---

## 4. Step C — Feature-neutrality checklist

**Criterion:** the bar is *feature neutrality with a direct connection*, not
"connects and streams". Run each row twice — once connected **directly** to the
PM5 and once **through the relay** — and compare.

| #   | Interaction                                | Direct | Relay | Identical? |
| --- | ------------------------------------------ | ------ | ----- | ---------- |
| 1   | Erg appears in the app's device list       |        |       |            |
| 2   | Device name / serial shown matches the erg |        |       |            |
| 3   | Connection completes without a retry       |        |       |            |
| 4   | Live stroke rate updates                   |        |       |            |
| 5   | Live pace / split updates                  |        |       |            |
| 6   | Live distance and elapsed time update      |        |       |            |
| 7   | Heart rate (if a strap is paired)          |        |       |            |
| 8   | Start a workout from the app               |        |       |            |
| 9   | Pause / resume mid-piece                   |        |       |            |
| 10  | Stop / end the workout                     |        |       |            |
| 11  | Interval or split boundaries render        |        |       |            |
| 12  | End-of-workout summary screen populates    |        |       |            |
| 13  | Workout saves / syncs to the C2 logbook    |        |       |            |
| 14  | Any other live-session screen in the app   |        |       |            |

Latency check: watch the erg's own PM5 display next to the phone. Metric
updates through the relay should track the display without a perceptible lag.
Note any consistent delay in seconds.

---

## 5. Step D — Extended-session stability

**Criterion:** the sole PM5 connection stays healthy for a realistic session.

1. Row a continuous piece of **at least 20 minutes** with the app connected
   through the relay.
2. Watch the periodic `RelayStats` lines:
   - `notifications_relayed` climbs steadily.
   - `notify_errors` stays at 0 (or is explained by a deliberate disconnect).
   - `unavailable_characteristics` does not change after startup.
3. Mid-session, background the Concept2 app and foreground it again. Confirm it
   reattaches without restarting the relay.
4. Optionally disconnect the app entirely and reconnect. The central-side PM5
   link must survive this — the relay is the sole holder of that link.

Record the final counters printed on Ctrl-C.

---

## 6. Step E — Document the gaps

**Criterion:** any app feature that does not work identically through the relay
is documented as a known gap, not silently dropped.

For every unchecked row in Step C, add an entry to `c2m-ooz.3` (or a new child
issue) recording:

- What differs (screen, metric, interaction).
- The relevant characteristic UUID(s), if identifiable from the capture.
- Which follow-up owns it: `c2m-hlj` (Fast-Follow Features) or `c2m-2rf`
  (Extended Features).

Only close `c2m-ooz.3` once Steps A–E are complete and every gap has a home.

---

## 7. Troubleshooting

| Symptom                                       | Likely cause                                                              |
| --------------------------------------------- | ------------------------------------------------------------------------- |
| `No PM5 found`                                 | Erg asleep, or another device already holds its single connection         |
| `adapter hci1 not found`                       | Dongle not enumerated — check `dmesg`, re-seat, `bluetoothctl power on`   |
| Advertising registration fails on `hci1`       | Kernel predates the #7473 fix — `rpi-update`, then re-check `uname -r`    |
| App sees the device but shows no metrics       | Wrong profile — revisit Step A and try `--profile ftms`                   |
| App connects then immediately drops            | Missing characteristic in the emulated set; compare against the capture   |
| Writes appear to succeed but the erg ignores them | Expected asymmetry: writes are acknowledged by the Pi, not the PM5 (see the script's "Known limitations") |

---

## 8. Record of runs

| Date | Kernel | PM5 firmware | Profile | Result | Notes |
| ---- | ------ | ------------ | ------- | ------ | ----- |
|      |        |              |         |        |       |
