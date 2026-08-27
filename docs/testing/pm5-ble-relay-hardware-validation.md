# PM5 BLE Relay — Hardware Validation Procedure

Manual test procedure for `c2m-ooz.3` (BLE peripheral relay). Everything here
needs physical hardware and therefore cannot be executed in CI or by an agent.
The automated unit tests cover the relay logic only; this document covers the
acceptance criteria that unit tests structurally cannot reach.

Everything below runs on the Raspberry Pi and the iPhone. No Mac, no Xcode, no
external BLE sniffer: the Pi *is* the GATT server the app connects to, so it
can observe the app's traffic directly.

**Context:** [ADR-003 — BLE Gateway Architecture](../adr/ADR-003-ble-gateway-architecture.md)

---

## 1. Hardware and environment

| Item           | Requirement                                                  |
| -------------- | ------------------------------------------------------------ |
| Host           | Raspberry Pi running the project image                       |
| Kernel         | `>= 6.18.42-v8+` (past the raspberrypi/linux#7473 regression) |
| Adapter `hci0` | Onboard controller — **central** role, holds the real PM5    |
| Adapter `hci1` | CSR8510-class USB dongle — **peripheral** role               |
| Erg            | Concept2 with PM5, firmware version recorded below           |
| Phone          | iPhone with the official Concept2 app installed              |

Pre-flight:

```bash
uname -r                       # must be >= 6.18.42-v8+
hciconfig -a                   # hci0 and hci1 both present
bluetoothctl power on
which btmon                    # ships with BlueZ; used in Step B
```

Wake the PM5 by pulling the handle. Make sure **no** other device (phone,
watch, previous session) is holding a connection to it — the PM5 accepts only
one, and this is the single most common cause of a failed run.

---

## 2. Step A — Bring up the relay

Run the relay with `--debug`, and keep the output: it is the evidence for
Step B.

```bash
uv run --with bleak --with bluez-peripheral \
    python docs/planning/legacy/examples/relay_pm5.py \
    --central hci0 --peripheral hci1 --profile pm5-proprietary --debug \
    2>&1 | tee ~/relay-run.log
```

Expected log sequence:

1. `Scanning for a PM5 on hci0` → `Found PM5 ... connecting`
2. `BLE relay started: profile=pm5-proprietary services=5 streaming=N/M`
3. `Advertising 'PM5 <serial> Row' on hci1`
4. `Relay live. Connect the Concept2 app to the advertised PM5.`

If `streaming=N/M` shows `N < M`, the connected firmware does not implement
every characteristic in the spec table. That is tolerated by design — note the
warned UUIDs, they are candidates for the known-gap list in Step E.

Every 10 s the script logs `RelayStats(...)`. Use those counters as the
objective evidence for the criteria below.

---

## 3. Step B — Confirm which service the app queries

**Criterion:** confirms which GATT service the official app actually queries —
the proprietary CSAFE family (`ce06xxxx`) or the standard Fitness Machine
Service (`0x1826`). Emulating the wrong one means the app will not recognise
the relay as a PM5 at all.

No packet sniffer is needed. The iPhone connects to the Pi's own BlueZ stack,
so the Pi sees every service discovery, read, write and subscription the app
performs. Two independent views, ideally captured in the same run:

### 3.1 Relay debug log (primary)

With `--debug` from Step A, every peripheral-side access is logged with its
UUID and characteristic name:

```
GATT read from consumer: ce060012-43e5-11e4-916c-0800200c9a66
Consumer write ce060021-43e5-11e4-916c-0800200c9a66 (C2 PM Receive Characteristic): 6 bytes
```

Connect the app to the advertised PM5, row a short piece, use start/pause/stop,
and visit every live-session screen. Then summarise what the app touched:

```bash
grep -oiE 'ce06[0-9a-f]{4}' ~/relay-run.log | sort | uniq -c | sort -rn
```

**Limitation:** the relay only serves the profile it is running, so this log
can only show accesses to services it emulates. Silence here is itself a
result — it means the app looked for something else. Cross-check with 3.2.

### 3.2 `btmon` HCI capture (cross-check)

`btmon` is a standard BlueZ tool, already on the Pi. Unlike the relay log it
also records what the app asked for and *did not find*: subscriptions (CCCD
writes), discovery of absent services, and `Attribute Not Found` errors.

Start it **before** connecting the app, in a second shell:

```bash
sudo btmon -i hci1 -w ~/relay-run.btsnoop | tee ~/relay-run-btmon.txt
```

Run the same app session, then Ctrl-C. Inspect the text log:

```bash
grep -iE 'ce06|1826|2ad1|Read By Group|Error response|Not Found' ~/relay-run-btmon.txt
```

The binary `~/relay-run.btsnoop` can be reopened later with `btmon -r`.

### 3.3 A/B the two profiles

If the app ignores or drops the relay, restart Step A with `--profile ftms` and
repeat. Whichever profile the app engages with — reads identity
characteristics, subscribes, streams — is the answer.

### 3.4 Record the outcome

- [ ] App uses the **proprietary** `ce06xxxx` services → keep the default
      `pm5-proprietary` profile.
- [ ] App uses **FTMS** `0x1826` → run the relay with `--profile ftms` and
      extend `_FTMS_SERVICES` in `packages/concept2mqtt/src/concept2mqtt/ble/profile.py`
      from the observed UUIDs (the FTMS table is currently marked UNVERIFIED).
- [ ] App uses **both** → note which characteristics come from which service;
      the profile registry can hold a combined profile.

Attach `~/relay-run.log` (or a written summary of the UUIDs seen) to
`c2m-ooz.3` before closing it.

---

## 4. Step C — Feature-neutrality check (user acceptance)

**Criterion:** the bar is *feature neutrality with a direct connection*, not
"connects and streams". This is a functional pass/fail check, deliberately
subjective — no protocol logs required.

Method: connect the app **directly to the PM5** first (relay off) and use it
normally, so you know what "normal" looks like. Then disconnect, start the
relay, connect the app **through the relay**, and repeat. Mark each row Pass if
it behaves the same as it did directly, Fail if it does not, and note anything
that feels different.

| #   | Behaviour through the relay                             | Pass/Fail | Note |
| --- | ------------------------------------------------------- | --------- | ---- |
| 1   | Erg appears in the app's device list under the same name |           |      |
| 2   | Connects on the first attempt, no retry or error dialog  |           |      |
| 3   | Live metrics update (stroke rate, pace, distance, time)  |           |      |
| 4   | Metrics track the PM5's own display without lag          |           |      |
| 5   | Heart rate shows (if a strap is paired)                  |           |      |
| 6   | Start / pause / resume / stop a workout from the app     |           |      |
| 7   | Interval and split boundaries render                     |           |      |
| 8   | End-of-workout summary screen populates                  |           |      |
| 9   | Workout saves / syncs to the C2 logbook                  |           |      |
| 10  | Every other live-session screen looks and behaves normal |           |      |
| 11  | No unexpected disconnects or error banners during use    |           |      |

For row 4, watch the erg's PM5 display next to the phone; note any consistent
delay in seconds. Anything marked Fail goes to Step E.

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

Record the final counters printed on Ctrl-C. Run this step without `--debug` if
the per-access log becomes unwieldy over 20 minutes.

---

## 6. Step E — Document the gaps

**Criterion:** any app feature that does not work identically through the relay
is documented as a known gap, not silently dropped.

For every Fail in Step C, add an entry to `c2m-ooz.3` (or a new child issue)
recording:

- What differs (screen, metric, interaction).
- The relevant characteristic UUID(s), if identifiable from the relay debug log
  or the `btmon` capture.
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
| App sees the device but shows no metrics       | Wrong profile — revisit Step B and try `--profile ftms`                   |
| App connects then immediately drops            | Missing characteristic in the emulated set; check `btmon` for `Not Found` |
| Relay debug log shows no reads at all          | App never got past discovery — the `btmon` capture (3.2) has the reason   |
| Writes appear to succeed but the erg ignores them | Expected asymmetry: writes are acknowledged by the Pi, not the PM5 (see the script's "Known limitations") |

---

## 8. Record of runs

| Date | Kernel | PM5 firmware | Profile | Result | Notes |
| ---- | ------ | ------------ | ------- | ------ | ----- |
|      |        |              |         |        |       |
