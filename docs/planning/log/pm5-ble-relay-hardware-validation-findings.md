# PM5 BLE Relay — Hardware Validation Findings (Runs 2026-09-05 / 2026-09-06)

Live findings log from the first real hardware execution of
[`docs/testing/pm5-ble-relay-hardware-validation.md`](../../testing/pm5-ble-relay-hardware-validation.md)
against `c2m-ooz.3`. Captures results, deviations, defects, and tooling lessons
so they can feed the requirements + implementation plan for the full
`concept2mqtt` app.

**Status (as of the 2026-09-05 session):** paused ~23:15. Steps A + B complete.
Step C functionally demonstrated once (see §11) but not re-verified — blocked
by a bonding / GATT-cache instability that makes every relay restart require a
both-sides bond wipe (§8). Step D not started. Two relay defects fully
characterised for the implementation plan: **(1) ~1 s added latency** vs
~0.15 s direct (§11.1), and **(2) connection instability across restarts**
(§8). Latency lever is app-controlled (`ce060034`), not ours (§11.1a).

**Update (2026-09-06, §14):** both defects root-caused and fixed. (1) was an
over-length consumer write (`ce060034`) being forwarded intact into a 1-byte
characteristic and rejected by the PM5 (`0x0D`) — truncating to the declared
length fixes it; the relay's own forward path was never the bottleneck
(1.2 ms mean). (2) was three defects in the peripheral shutdown/pairing path,
peripheral-side hardware-verified (§14.3). A third defect — SIGINT/SIGTERM
being silently ignored — was found and fixed in the same session (§14.5).
None of this has an end-to-end iPhone re-verification yet; that is
`c2m-ooz.3.3`.

### TL;DR for planning

| Area | Outcome |
| --- | --- |
| App discovery | Needs 128-bit `ce060000` in the ADV; legacy adapter can't fit the real PM5's full packet → name truncated to "PM5" |
| App protocol | Proprietary `ce06xxxx` only; no FTMS. Writes CSAFE to `ce060021`, sample rate to `ce060034` |
| Functional relay | Works — connects, streams all rowing data incl. workout summary, start/pause/stop, zero notification drops in a clean session |
| Latency | **Relay adds ~1 s (direct ≈ 0.15 s).** Root cause found and fixed 2026-09-06 (§14.5): the app's 8-byte `ce060034` write was rejected by the PM5 for exceeding the declared 1-byte length. Relay's own forward path measures 1.2 ms mean / 4.2 ms max. Pending `c2m-ooz.3.3` end-to-end re-verification |
| Stability | **Every restart needs a both-sides Bluetooth bond wipe or the app won't connect.** Fixed 2026-09-06 (§14.1); peripheral-side hardware-verified (§14.3). End-to-end iPhone re-verification pending `c2m-ooz.3.3` |
| Pairing | Relay bonds; should be "just works" / non-bondable |
| Firmware | `ce06003c` (HR belt) not implemented on FW `8200-000409-217.067` — tolerated |

---

## 1. Environment

| Item | Value |
| --- | --- |
| Host | Raspberry Pi, SSH `<PI-SSH-REDACTED>` (`edge-04`) |
| Kernel | `6.18.42-v8+` (past raspberrypi/linux#7473) |
| `hci0` | Broadcom UART onboard — central, holds real PM5 (`88:A2:9E:B5:49:48`) |
| `hci1` | CSR8510-class USB dongle — peripheral (`00:1A:7D:DA:71:13`), **BT 4.0, legacy advertising only** |
| Erg / PM5 | serial `530426599`, HW rev `907`, FW `8200-000409-217.067`, BLE addr `D9:1A:D2:36:50:4A` (random static) |
| Phone | iPhone (`D0:88:0C:0D:CA:29`), official Concept2 app |
| Relay entrypoint | `uv run --with bleak --with bluez-peripheral python docs/planning/legacy/examples/relay_pm5.py --central hci0 --peripheral hci1 --profile pm5-proprietary --debug` |
| Python / libs | Python 3.13.5, bleak, bluez-peripheral, dbus-next |

Working-tree state on the Pi during the run differs from committed code — see
§5 (code changes made mid-session to get the relay to work).

---

## 2. Step A — Bring up the relay — **PASS (with notes)**

Startup sequence observed exactly as documented:

```
relay Found PM5 530426599 Row (D9:1A:D2:36:50:4A); connecting...
relay Advertising 'PM5 530426599 Row' on hci1 as pm5-proprietary
concept2mqtt.ble.relay BLE relay started: profile=pm5-proprietary services=5 streaming=15/16
relay Relay live. Connect the Concept2 app to the advertised PM5.
```

- `streaming=15/16` — 15 of 16 subscribable characteristics active.
- `unavailable_characteristics=1` — **`ce06003c` is not implemented by this
  firmware** (`PM5 does not stream ce06003c-...; skipping`,
  `BleakCharacteristicNotFoundError`). Known firmware gap → Step E candidate.
- `RelayStats` `notifications_relayed` climbs steadily (~8/s at idle from PM5
  status notifications).

### Defect A1 — notification/registration startup race
`notify_errors` jumps to ~22–26 in the first ~3 s after the central subscribes,
then **freezes and never grows again**. Cause: the relay subscribes to PM5
notifications before the peripheral GATT table is fully registered, so the first
burst hits `KeyError` in `relay_pm5.py` `notify()`
(`self._characteristics[uuid].changed(data)`) and
`concept2mqtt.ble.relay._on_notification` logs `Dropped notification for
ce0600xx`. Affected UUIDs in the burst: `ce060031`, `ce060032`, `ce060033`,
`ce06003e`, `ce060022`. Impact: first ~5 s of telemetry after startup is lost;
harmless for a rowing session but must be fixed for a clean implementation
(order: register peripheral + advertise *before* `start_notify` on the central,
or queue early notifications).

---

## 3. Step B — Which GATT service does the app use? — **RESULT: proprietary `ce06xxxx`**

**Every** GATT access from the Concept2 app is on the proprietary Concept2
services. **Zero** FTMS (`0x1826` / `2ad1`) traffic after connection.

→ Doc checkbox: **App uses the proprietary `ce06xxxx` services → keep the
default `pm5-proprietary` profile.** Confirmed on hardware.

### 3.1 What the app read (identity / info)
`ce060011` Model Number · `ce060012` Serial Number · `ce060013` Hardware Revision
· `ce060014` Firmware Revision · `ce060015` Manufacturer Name · `ce060016` Erg
Machine Type · `ce060017` ATT MTU · `ce060018` LL DLE · `ce060022` C2 PM Transmit.
(Re-read several of these a second time right after connecting.)

### 3.2 What the app wrote
- `ce060021` **C2 PM Receive Characteristic** — 3 writes (8, 16, 10 bytes).
  CSAFE command channel; forwarded to the PM5 (`writes_relayed` 0 → 3).
- `ce060034` **Rowing General/Additional Status Sample Rate** — 2–3 writes
  (8 bytes). App configuring the notification cadence.

### 3.3 What the app did NOT do (yet — pre-rowing)
No CCCD/subscribe lines captured in the identity phase (bleak/BlueZ may not log
peripheral-side CCCD writes the same way; cross-check pending). No `0x1826`
access at all.

### 3.4 Discovery finding (separate from GATT usage)
The app **scans with a filter on the 128-bit `ce060000-43e5-11e4-916c-0800200c9a66`
service UUID**. The relay was invisible in the app's device list until that UUID
was placed in the advertising data. Sequence of what did / didn't work:

| Advertised | App sees it? |
| --- | --- |
| `ce060030` 128-bit UUID only (original profile) | not tested this run |
| `0x1826` 16-bit UUID only | **No** |
| `0x1826` UUID + `0x1826` Service Data (`01 10 00`) | **No** |
| `ce060000` 128-bit UUID + `0x1826` Service Data | BlueZ **rejects advert** (too big for legacy 31 B) |
| `ce060000` 128-bit UUID + short name "PM5", no service data | **Yes** — app lists + connects |

The real PM5's own advertisement (captured 2026-09-05, see §4) carries name +
16-bit `0x1826` + 128-bit `ce060000` + `0x1826` Service Data + Appearance +
TX Power in **one BLE-5 extended-advertising PDU (58 B payload)**. The CSR8510
dongle only does **legacy advertising (31 B + 31 B scan response)** and cannot
reproduce that packet. Minimum that satisfies discovery: **`ce060000` 128-bit
UUID in the ADV data.** The `0x1826` Service Data (Fitness Machine Type = rower)
turned out **not** to be required for discovery by this app version.

---

## 4. Real PM5 advertisement (reference capture)

`btmon -i hci0` while scanning, relay stopped. Address `D9:1A:D2:36:50:4A`
(static random), `ADV_IND` (connectable), BLE-5 extended advertising:

```
ADV_IND payload (58 B):
  Appearance:            0x0000
  Flags:                 0x06 (LE General Discoverable, BR/EDR not supported)
  TX Power:              4 dBm
  Name (complete):       "PM5 530426599 Row"
  16-bit Service UUIDs:  0x1826
  128-bit Service UUIDs: ce060000-43e5-11e4-916c-0800200c9a66
  Service Data (0x1826): 01 10 00      # flags=0x01, Fitness Machine Type=0x0010 (rower)
```

GATT services on the real PM5 (from BlueZ dump): `1800`, `1801`, `1826`,
`ce060000`, `ce060010`, `ce060020`, `ce060030`, `ce060040`. **`ce060000` is a
real service on the PM5 and is not currently in the relay's `_PM5_SERVICES`
table** (relay serves 5: `ce060010/20/30/40` + `1826`).

---

## 5. Code changes made during the session (Pi working tree only — not committed)

These were needed to get the relay to run/be discoverable. They need proper
review before landing.

1. **`profile.py` — advertise `ce060000`.**
   `advertised_service_uuids=(pm5_uuid(0x0000),)` (was `sig_uuid(0x1826)` from a
   prior lost session; originally `pm5_uuid(0x0030)`). `advertised_service_data`
   set back to `{}` — could not be advertised alongside the 128-bit UUID in
   legacy mode.

2. **`relay_pm5.py` — `_ServiceDataAdvertisement` subclass.** `bluez-peripheral`
   declares `org.bluez.LEAdvertisement1.ServiceData` with D-Bus signature
   `a{say}`; BlueZ requires `a{sv}` (byte arrays wrapped in variants) and
   rejects the whole advert with *"Failed to parse advertisement"*. Subclass
   overrides `ServiceData` to emit `a{sv}`. **Currently unused** (service data
   dropped) but keep — needed if a future app version requires the FTMS service
   data, and it is a genuine upstream bug.

3. **`relay_pm5.py` — short advertised name.** Advertise
   `profile.device_name.split()[0][:8]` (→ "PM5") instead of the full
   "PM5 530426599 Row". A 128-bit UUID (18 B) + full name (19 B) + flags
   overflow the 31 B legacy packet and BlueZ returns *"Failed to register
   advertisement"*. Full name still served over GATT / adapter alias.

4. **`relay_pm5.py` — `_resolve_adapter` rewrite** (carried from the lost
   session). `Adapter.get_all()` chokes on this BlueZ build's non-adapter
   `/org/bluez/test` (`SimAccessTest1`) node before it reaches `hci1`; replaced
   with a direct `bus.introspect("org.bluez", "/org/bluez/hciN")`.

---

## 6. Deviations from a direct PM5 connection (Step C seeds)

| # | Behaviour | Direct PM5 | Through relay | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Name in device list | "PM5 530426599 Row" | **"ID edge-04"**, then "ID 530426599" after connect | **Fail (cosmetic)** — advertised name truncated to "PM5"; app fell back to controller name `edge-04` |
| 2 | Connect on first attempt, no dialog | just-works, silent | **iOS pairing/bonding prompt** shown, user must accept; `hci1` link ends up `AUTH ENCRYPT` | **Partial** — connects, but extra dialog. Caused by relay agent + bondable adapter |

Rows 3–11 of Step C (live metrics, start/pause/stop, splits, summary, logbook
sync, disconnects) — **pending, user rowing now.**

---

## 7. Confirmed relay behaviour (positive)

At the point the app was connected and idle:
- `hci1` peripheral link to iPhone: `state 1 lm PERIPHERAL AUTH ENCRYPT`.
- `hci0` central link to PM5: `Connected = true` throughout — relay never
  dropped the sole PM5 connection.
- `notifications_relayed` climbing (992 → 1313 over ~40 s), `notify_errors`
  flat at 26 (all from the startup race), `writes_relayed` 0 → 3 as the app
  issued CSAFE writes.
- App displays the PM5's real serial (`530426599`) — served by the relay from
  values prefetched from the PM5 at startup.

Architecture proven: **iPhone ⇄ Pi `hci1` (peripheral) ⇄ Pi `hci0` (central) ⇄ PM5.**

---

## 8. Operational / tooling lessons (for the run doc + implementation)

- **No `tmux`/`screen` on the Pi.** Relay launched with
  `setsid bash -c 'exec ... > ~/relay-run.log 2>&1' </dev/null & disown`.
  Stop cleanly with `pkill -INT -f 'relay_pm5.py --central'` so it runs its
  shutdown (prints Final counters, disconnects central). `SIGKILL` skips
  cleanup — see next point.
- **Killing the relay ungracefully leaves the PM5 connected on `hci0`.** BlueZ
  keeps the ACL link; the next relay run then fails its *scan* step with
  `No PM5 found` because the PM5 is connected, not advertising. Fix before every
  restart: `bluetoothctl disconnect D9:1A:D2:36:50:4A`.
- **The relay does not auto-reconnect** to the PM5 after a central-side drop.
  In the earlier crashed session the PM5 dropped at 21:53 and the relay sat idle
  (stats frozen) for 4 h without recovering. → hard requirement for the real app.
- **Ungraceful kill leaves a stale advertising registration on `hci1`.** The
  next `RegisterAdvertisement` then fails intermittently with BlueZ
  `org.bluez.Error.Failed` *"Failed to register advertisement"* (distinct from
  *"Failed to parse advertisement"*, which is the size/signature problem). Clear
  it with `hciconfig hci1 down && hciconfig hci1 up` before each start. Added to
  the restart routine. Root cause: bluez-peripheral registers at a fixed D-Bus
  path and never unregisters on crash.
- **Bonding reconnection trap.** The iPhone bonds on first connect (`hci1` link
  ends `AUTH ENCRYPT`). After a relay restart the phone silently auto-reconnects
  that bond at the link layer, but the GATT session is stale and the app does
  not re-run discovery. A connectable advert stops broadcasting once it has a
  connection, so the device **disappears from the app's scan** — symptom: "app
  cannot find the device" even though `ActiveInstances=1`. Recovery: on the Pi
  disconnect the phone (`hcitool -i hci1 ledc <handle>`) and, on the iPhone,
  **"Forget This Device"**. → the emulated peripheral should be **non-bondable
  / "just works"** (see R-PAIR-1).
- **Every relay restart currently needs a full bond wipe on BOTH sides** to get
  a working connect. Observed repeatedly (22:46, 23:09): after a restart the app
  finds the device and the pairing prompt appears, the user accepts, and then
  **the connection never completes** (no GATT discovery, no `Consumer read`).
  The only reliable recovery seen: stop relay → `rm -rf
  /var/lib/bluetooth/<hci1-addr>/<phone-addr>` and
  `/var/lib/bluetooth/<hci1-addr>/cache/*` → `systemctl restart bluetooth` →
  restart relay → **"Forget This Device" on the iPhone** → connect fresh. Two
  successful rows (22:31, 22:59) each came *immediately after* such a wipe.
  Likely cause: bluez-peripheral assigns GATT handles dynamically, so the
  attribute layout shifts across restarts; iOS keeps its cached layout for a
  bonded peripheral and there is no working Service Changed path, so discovery
  breaks. **This is the top blocker for Steps C-retest / D and a primary
  implementation requirement** — see R-PAIR-1, R-GATT-STABLE-1.
- `systemctl restart bluetooth` **kills the relay's BlueZ registrations** (advert
  + GATT server) without killing the process; the relay does not re-register.
  Always restart the relay after touching the `bluetooth` service.
- **`uv` is not on the non-login `PATH`** (`~/.local/bin/uv`). `ssh host 'cmd'`
  and `bash script.sh` need the absolute path or a login shell.
- **`btmon` under `setsid` produced no text output**; the binary `-w`
  `.btsnoop` capture works and is read back with `btmon -r file`. `sudo` is
  NOPASSWD for `fab`.
- **`btmon` on `hci1` also shows BR/EDR EIR writes** ("PM5 530426599 Row" + "6
  16-bit UUIDs") whenever BlueZ rewrites the adapter's classic inquiry data —
  this is *not* the LE advertisement; do not confuse the two.
- A prior VSCode crash orphaned a relay that kept running on the Pi for ~4.5 h.
  Its log (`~/relay-run-20260905-crashed.log`) was preserved.

Log files on the Pi: `~/relay-run.log` (current), `~/relay-run-<HHMMSS>.log`
(rotated per restart), `~/relay-run*.btsnoop`, `~/pm5-real-adv.btsnoop`
(reference capture from §4).

---

## 9. Open questions

- Does the app subscribe (CCCD) to specific `ce06xxxx` notify characteristics,
  and which? Need a cleaner capture during active rowing.
- What are the CSAFE payloads the app writes to `ce060021` (8/16/10 B)? Decode
  against the `docs/planning/spec/csafe` tables.
- Does the app misbehave because `ce060000` is advertised but not served? (Watch
  for a disconnect right after connect during Step C.)
- Is the pairing prompt avoidable (non-bondable adapter / different agent), and
  does the real PM5 actually bond or use "just works" LE Secure Connections?
- Can the full name be advertised via a scan response the app reads before
  connecting (so it lists as "PM5 530426599 Row"), within legacy limits?

---

## 10. Implications for the full `concept2mqtt` app (requirement seeds)

Draft — to be firmed up after Steps C–E.

- **R-DISC-1** Peripheral advertisement MUST include the 128-bit
  `ce060000-43e5-11e4-916c-0800200c9a66` service UUID in the primary ADV data;
  the Concept2 app scan-filters on it. 16-bit `0x1826` alone is insufficient.
- **R-DISC-2** With a legacy-only adapter the advertised local name MUST be
  short enough that `flags + 128-bit UUID + name` fit 31 B; document the
  trade-off (device lists as "PM5", full name only over GATT). Prefer an adapter
  with BLE-5 extended advertising to match the real PM5 packet.
- **R-PAIR-1** The emulated peripheral SHOULD be non-bondable ("just works", no
  stored keys) so a relay restart does not strand a bonded consumer on a dead
  link (the "bonding reconnection trap", §8). Confirm whether the real PM5
  bonds or uses just-works. **Blocking:** in this run every restart needed a
  both-sides bond wipe before the app could connect.
- **R-GATT-STABLE-1** The emulated GATT database MUST present a **stable
  attribute layout** across relay restarts (fixed handles), or implement a
  Service Changed indication iOS honours — otherwise a bonded iOS client keeps a
  stale cache and connection completion fails after re-pair. bluez-peripheral's
  dynamic handle assignment is insufficient as-is.
- **R-OPS-2** On startup the relay MUST clear any stale advertising registration
  on the peripheral adapter (equivalent of `hciconfig <hci> down/up`), and on
  shutdown MUST unregister the advertisement and disconnect both links.
- **R-OPS-3** On any consumer disconnect the relay MUST resume advertising
  promptly so the app can re-discover it without manual intervention.
- **R-PROFILE-1** Emulated GATT server MUST expose the proprietary `ce06xxxx`
  services. FTMS emulation is not required for the official app. Add `ce060000`
  to the served service set.
- **R-RELAY-1** Notifications from the PM5 MUST NOT be lost during startup:
  register + advertise the peripheral before subscribing on the central, or
  buffer.
- **R-RELAY-2** MUST auto-reconnect the central PM5 link on drop, with backoff,
  without tearing down the peripheral, and resume relaying.
- **R-RELAY-3** MUST shut down cleanly on SIGINT/SIGTERM: disconnect the central
  link so the PM5 is immediately re-connectable. **Fixed 2026-09-06 (§14.5):**
  `KeyboardInterrupt` does not fire under `setsid` with no controlling
  terminal, so SIGINT was silently ignored and SIGTERM unhandled — every prior
  "clean" stop actually left the PM5 connected. Explicit `asyncio` signal
  handlers now cover both.
- **R-RELAY-4** Tolerate firmware that does not implement every spec
  characteristic (`streaming=N/M`, `ce06003c` absent here); surface the gap,
  keep running.
- **R-OPS-1** Ship as a managed long-running service (systemd unit), not a
  detached script; structured logs; periodic stats.
- **R-TEST-1** The `btmon`/relay-log method in the run doc is sufficient to
  observe app behaviour without a Mac or external sniffer — keep it.
- **Upstream** File / carry a patch for `bluez-peripheral`'s `ServiceData`
  D-Bus signature bug (`a{say}` → `a{sv}`).

---

## 11. Step C results — feature neutrality — **PASS (usable), with the deviations in §6**

Session ~22:31–22:42, "Just Row" (no planned workout), short piece, then
start/pause/resume/stop, saved at the end.

**User-observed (phone):**
- App behaves normally throughout. Live metrics update. Start/pause/resume/stop
  all work from the app.
- **Latency PM5 display → app ≈ 1.1–1.3 s.** User rates it "borderline
  acceptable". Analysis below.
- **Logbook:** user did **not** see the row appear in the C2 logbook
  afterwards. Unresolved — most likely the piece was too short (C2 does not log
  trivially short rows) and/or a separate app→cloud sync concern; the relay is
  not implicated (see below). Re-test with a ≥2 min / ≥500 m piece.

**Relay-side (from `~/relay-run.log`, whole session):**
- `notify_errors` **flat at 26** across 4944 relayed notifications — zero drops
  during rowing or at workout end. The 26 are all the §2 startup race.
- Every rowing characteristic relayed, including end-of-workout data:

  | Characteristic | Events | Note |
  | --- | --- | --- |
  | `ce060031/32/33` General + Additional Status | 1234 each | steady ~1 Hz |
  | `ce060035` Stroke Data | 23 | per-stroke |
  | `ce060036` Additional Stroke Data | 14 | |
  | `ce060037/38` Split/Interval Data | 2 each | |
  | `ce060039/3a/3b` **Workout Summary** | 2 each | **end-of-workout summary reached the app** |
  | `ce06003e` Force Curve | 1234 | streams continuously |
  | `ce06003d` | 79 | |

- App writes during the session: `ce060021` (C2 PM Receive / CSAFE) — 11–17 B
  each, for start/pause/stop; all forwarded to the PM5
  (`bleak ... Write Characteristic ce060021 ... b'\xf0\xfd\x00v\x04...'`).
- App also wrote `ce060034` (Sample Rate) twice, **8 bytes each**, early in the
  session. `relay._on_write` forwards all writable characteristics, so these
  reached the PM5 — but the PM5's status rate stayed at 1 Hz (see §11.1). The
  8-byte write to a 1-byte characteristic is unexplained (app quirk, or PM5
  rejected the malformed write).

→ Step C checklist: rows 3, 6, 7, 8 (metrics, start/pause/stop, splits, summary)
**Pass** at the relay level. Row 4 (lag) **borderline**. Row 9 (logbook)
**inconclusive**. Rows 1–2 **Fail/partial** per §6.

### 11.1 Latency analysis — the ~1.1–1.3 s

> **CORRECTION (direct-connection baseline, 23:1x).** With the relay **off**, the
> iPhone connected **directly to the real PM5** and the user measured the
> display→app lag at **~0.1–0.2 s** while rowing. So the ~1.2 s seen through the
> relay is **~1 s added by the relay**, *not* the PM5's inherent update cadence.
> The "PM5 emits at 1 Hz" observation below was measured **on the relay's own
> central link during a relay session** — i.e. the PM5 was *already* only being
> asked for ~1 Hz on that path. Direct, the app negotiates a fast rate and gets
> it. Leading hypotheses for the ~1 s relay penalty:
>
> 1. **The app's `ce060034` sample-rate write does not take effect through the
>    relay.** Direct, the app writes `ce060034` and the PM5 speeds up. Through the
>    relay the same write is logged as 8 bytes and forwarded, but the PM5 keeps
>    streaming General Status at ~1 Hz — so the relayed write is being rejected
>    or mangled (wrong length/'`write` vs `write-without-response`'/timing), and
>    the PM5 stays at its 1 s default. This alone would produce ~1 s.
> 2. **The relay's forward path adds fixed buffering/latency** (bleak
>    `PropertiesChanged` in → asyncio → bluez-peripheral `notify` D-Bus call out
>    → BlueZ → 30 ms legacy link), which the sample-rate quick test (§11.1a)
>    made *worse* not better.
>
> Both are relay defects to fix, not inherent limits. Next: capture the app's
> exact `ce060034` write on a direct connection, and compare PM5→central
> notification rate direct vs through the relay.

Measured on the Pi during the (relay-connected) session:

| Contributor | Measured | Notes |
| --- | --- | --- |
| **PM5 status sample period** | **exactly 1 Hz** on `ce060031` (`+1s/+0s` inter-arrival) | `ce060034` Sample Rate reads back `0x01`. **Dominant term.** |
| BLE connection interval, `hci0`↔PM5 | **30 ms** | supervision 720 ms |
| BLE connection interval, `hci1`↔iPhone | **30 ms** | supervision 720 ms |
| Relay software path | not isolated, est. 30–100 ms + jitter | bleak `PropertiesChanged` in → asyncio → bluez-peripheral `notify()` D-Bus call out → BlueZ; **plus synchronous `--debug` file logging on every notification** (log grew ~5 MB in the session) |

So ~1 s of the ~1.2 s is the **PM5's own update cadence**, not the proxy. A
*direct* app↔PM5 connection at the same sample rate would see the same ~1 s. The
relay's true added cost is roughly one extra BLE hop + the software path,
~100–150 ms.

**Levers to reduce it, highest impact first:**

1. **Raise the PM5 sample rate.** `ce060034`: `0`=1 s, `1`=500 ms, `2`=250 ms,
   `3`=100 ms (C2 CSAFE PM BLE spec). Have the relay **proactively write
   `ce060034` = 2 or 3 to the PM5 at startup** rather than waiting for the app,
   and make the app's own sample-rate writes pass through in a form the PM5
   accepts (investigate the 8-byte write). Floor drops from ~1000 ms to
   ~100–250 ms.
2. **Run without `--debug`** in normal operation — removes per-notification
   blocking disk I/O from the forward path. Keep `--debug` only for protocol
   captures.
3. **Request a tighter connection interval** (~15 ms, or 7.5 ms min) on both
   links via an LE connection-parameter update. Saves ~30–45 ms.
4. **Longer term:** cut D-Bus overhead in the hot path — BlueZ
   `AcquireNotify` / `AcquireWrite` FD pipes, or a lower-level transport instead
   of `PropertiesChanged` + method calls. Shaves tens of ms and jitter.

Realistic post-fix total: **~200–350 ms** — comfortably better than borderline.

### 11.1a Sample-rate quick test — **DID NOT HELP; latency got worse**

Tried writing `ce060034 = 3` to the PM5 from the relay at startup
(`C2M_SAMPLE_RATE` env, `run()` patch). Findings:

- **The PM5 retains `ce060034` across relay reconnects** (read back `0x03` on a
  later run without re-writing). It is *not* reset on erg wake; likely only on
  full power-off or a specific CSAFE command.
- **The Concept2 app manages the sample rate itself.** On every connect it
  writes `ce060034` — an **8-byte** payload — twice, immediately after reading
  identity (seen at 23:00:24–25 and in the 22:31 session). The relay forwards
  it (`_on_write` passes all writable chars through). So the relay's startup
  write only governs the brief pre-connect window; the app's value wins.
- With the rate forced high, the user's next row measured **~3 s lag,
  fluctuating** (vs the ~1.2 s steady baseline). `notifications_relayed` held a
  *steady* ~11–12/s (no runaway backlog in the counter), so the extra latency
  is a **fixed pipeline delay + jitter**, not an unbounded queue — consistent
  with BlueZ notification queuing over a bandwidth-limited 30 ms legacy link
  and/or `--debug` synchronous logging amplified by the higher event rate.
- The 8-byte write to a nominally 1-byte characteristic is still unexplained
  and may itself be mishandled (PM5 rejects / partially applies) — needs the
  CSAFE spec.

**Revised conclusion:** the sample rate is **not a lever we control** — the app
sets it. The ~1.2 s baseline is close to what the app itself asks for plus relay
overhead. Reducing it requires (a) removing `--debug` / any synchronous hot-path
logging, (b) cutting per-notification D-Bus cost (`AcquireNotify`/`AcquireWrite`
FD pipes or lower-level transport), (c) BLE connection-parameter tuning — and
verifying the relay does not add queuing delay under load. A naive sample-rate
increase is counter-productive on this transport.

Also observed: **a fresh re-pair may renegotiate slower BLE connection
parameters** than the first session (could not confirm — `btmon` capture was
unreliable this run). Track separately.

### 11.2 Logbook — why the relay is probably not at fault

The workout-summary characteristics (`ce060039/3a/3b`) did relay to the app
(2 notifications each, no drops). Logbook persistence then happens in the app
and its sync to the Concept2 cloud over the internet — outside the BLE path.
Most likely: the "Just Row" piece was below Concept2's minimum logged
distance/duration. **Action:** re-row a ≥2 min / ≥500 m piece with the app
through the relay and confirm it appears in the logbook (and check the app's
"unsynced workouts" view).

---

## 12. Step D results

_pending — 20-minute continuous piece, app backgrounding, reconnect_

---

## 13. Additional requirement seeds (from Step C)

- **R-LATENCY-1** ~~The relay SHOULD set the PM5 status sample rate to a fast
  value at startup~~ **Superseded (§11.1a):** the app sets `ce060034` itself on
  every connect; a relay-forced fast rate is overridden and, tried standalone,
  *increased* perceived latency on this transport. ~~The relay MUST forward
  the consumer's `ce060034` writes intact and MUST NOT add its own rate
  policy.~~ **Revised (§14.5):** that wording turned out to be the bug —
  forwarding the app's 8-byte write intact into a characteristic the PM5
  declares as 1 byte is what triggered the `0x0D` rejection that kept the erg
  at 1 Hz. The relay MUST honour each characteristic's declared length
  (truncating an over-length consumer write, as the real PM5 would enforce at
  the ATT layer) and MUST NOT otherwise reinterpret or rate-limit what the
  consumer asked for — clamping length is not the same as adding a rate
  policy.
- **R-LATENCY-2** Production operation MUST NOT do synchronous per-notification
  logging on the forward path (structured logging must be async / rate-limited /
  off by default).
- **R-LATENCY-3** The relay SHOULD negotiate a short LE connection interval
  (~15 ms) on both links.
- **R-LATENCY-4** End-to-end added latency through the relay MUST be small
  relative to a direct connection. **Measured baseline: direct ≈ 0.15 s, relay
  ≈ 1.2 s — the relay adds ~1 s and that is a defect, not a limit.** Target: relay
  adds < ~0.2 s. **Root cause found and fixed 2026-09-06 (§14.5)** — the
  relay's own forward path measures 1.2 ms mean / 4.2 ms max, so the target is
  already met on the software side; end-to-end re-measurement with the app is
  `c2m-ooz.3.3`.
- **R-LATENCY-5** The consumer's `ce060034` (sample-rate) write MUST reach the
  PM5 in a form the PM5 honours — verify the relayed write actually raises the
  PM5's notification rate (it did not this run; PM5 stayed ~1 Hz on the relay's
  central link while a direct client gets the fast rate). **Fixed 2026-09-06
  (§14.5):** the write reached the PM5 unhonoured because it exceeded the
  declared length (`0x0D` Invalid Attribute Value Length); truncating to the
  declared length is what the direct-connection contract already enforces.
  Whether the PM5 then actually speeds up end-to-end through the relay is
  `c2m-ooz.3.3`.
- **R-DATA-1** All rowing-service notify characteristics
  (`ce060031`–`ce06003f`, incl. stroke, split/interval, workout-summary, force
  curve) MUST relay unmodified — confirmed working this run.
- **R-LOGBOOK-1** Validate end-to-end logbook capture with a non-trivial piece
  before declaring Step C fully passed.

---

## 14. Fixes landed 2026-09-06 (not yet hardware-verified)

Written against this log, in the dev container — the Pi was unreachable, so
**none of this is confirmed on hardware**. The `c2m-ooz.3.3` re-run is what
validates it.

### 14.1 `c2m-ooz.3.2` — connection unstable across restarts

Three defects in the peripheral binding, all in `relay_pm5.py`:

| # | Defect | Effect |
| --- | --- | --- |
| 1 | `NoIoAgent` was registered, adapter left bondable | iOS bonded, then trusted its cached attribute layout instead of re-discovering — the §8 trap |
| 2 | `stop()` called `Advertisement.release()`, which **does not exist** in bluez-peripheral; `contextlib.suppress` swallowed the `AttributeError` | the advertisement was never unregistered, even on a clean `SIGINT` |
| 3 | `stop()` called the **async** `ServiceCollection.unregister()` without awaiting it | the GATT application was never unregistered either |

Defects 2 and 3 are why §8's "ungraceful kill leaves a stale advertising
registration" was really "*every* shutdown leaves one".

Fixes: no pairing agent, `Pairable=false`, forget devices already bonded to the
peripheral adapter at startup, power-cycle the adapter on startup (the scripted
`hciconfig down/up`), and unregister both the advert (via
`LEAdvertisingManager1`) and the GATT application on shutdown, logging failures
instead of suppressing them.

**Expected at the next run:** no pairing prompt, no bond, and a relay restart
that needs no wipe on either side. If the app still fails to connect after a
restart, R-GATT-STABLE-1 (fixed handles / Service Changed) is the remaining
cause and `c2m-ooz.3.2` should be reopened against it.

### 14.2 `c2m-ooz.3.1` — ~1 s added latency

> **Superseded by §14.5.** At the time this section was written the root cause
> was not established. The next hardware run (still 2026-09-06) confirmed
> hypothesis 1 directly and the fix landed — see §14.5. Left as-is below for
> the record of how the measurement was made instrumentable.

This run's instrumentation could not by itself have established the root
cause: `notifications_relayed` counted every forward, including
the ones bluez-peripheral silently discarded because the consumer had not
subscribed. So the §11 per-UUID table shows what the relay *pushed*, not what
reached the air, and the "relay software path" row in §11.1 was never measured
at all. Changes are therefore split between removing a known cost and making
the rest measurable.

Removed:

- `--debug` raised the **root** logger, which turned on bleak's and dbus-next's
  DEBUG output — a line written synchronously to disk per BLE notification, on
  the forward path (the ~5 MB log in §11.1). It now raises only `relay` and
  `concept2mqtt`. This is R-LATENCY-2, and it was worse than §11.1 assumed:
  the volume came from the libraries, not from our own handlers.
- The startup ordering that caused Defect A1: the peripheral is registered
  before the central subscribes, so the PM5's opening burst has somewhere to
  go (R-RELAY-1).

Made measurable:

- Notifications are forwarded only to characteristics the consumer actually
  subscribed to; `notifications_withheld` counts the rest, and each
  subscribe/unsubscribe is logged at INFO. **This answers open question §9 #1
  directly** — the next run's log says which streams the app uses.
- `forward_seconds_total` / `forward_seconds_max` (reported as
  `forward_ms(mean=… max=…)`) isolate the relay's own software path, the
  unmeasured row of the §11.1 table.
- `write_errors` counts writes the PM5 rejected, and the relay now warns when
  a consumer writes more bytes than the characteristic holds. **This is the
  test for hypothesis 1**: the app's 8-byte write to the 1-byte `ce060034`
  (spec: `bytes: 1`) should now show up as both a warning and a rejection. The
  relay previously dispatched writes fire-and-forget and never looked at the
  result, so a PM5 rejection was invisible while the app got an ACK from the
  Pi. A 1-byte write from the relay *did* take effect (§11.1a read back
  `0x03`), so an over-long write being refused is consistent with everything
  observed.

**Next run should record:** `forward_ms` mean/max, `notifications_withheld` vs
`notifications_relayed`, `write_errors`, the subscribe lines, and whether the
over-length warning fires on `ce060034`. If `write_errors` climbs with
`ce060034` and the PM5 stays at 1 Hz, hypothesis 1 is confirmed and the fix is
a relay-side sample-rate translation — which R-LATENCY-1 currently forbids, so
that requirement would need revisiting.

### 14.3 Hardware verification of §14.1 (2026-09-06, edge-04 at `<PI-IP-REDACTED>`)

`BluezPeripheralServer` exercised standalone on `hci1` — no PM5 involved, so
this covers the peripheral-side claims only:

| Check | Result |
| --- | --- |
| `Pairable` / `Discoverable` after startup | `False` / `False` — the non-bondable fix works, and needs no extra polkit privilege |
| `ActiveInstances` while running | `1` |
| `ActiveInstances` after `stop()` | **`0`** — the advertisement really is unregistered. Under the old code `Advertisement.release()` raised `AttributeError` into `contextlib.suppress`, so this stayed `1` for the life of the daemon |
| 3 consecutive start/stop cycles | **PASS**, 0 failures, no warnings from `stop()` — the "Failed to register advertisement" restart failure is gone |

Still unverified, because it needs the iPhone: that the app connects with no
pairing prompt and reconnects after a relay restart without a both-sides wipe.
That is the end-to-end claim and belongs to `c2m-ooz.3.3`.

### 14.4 `c2m-ooz.3.5` — reconnect and resume advertising

The relay had no disconnect handling at all: `run()` awaited
`asyncio.Event().wait()` forever and the `BleakClient` was built without a
`disconnected_callback`. That is why §8's PM5 drop at 21:53 left it dead for
4 h.

- **R-RELAY-2.** A `disconnected_callback` now wakes a supervisor loop that
  rescans and reconnects with exponential backoff (2 s → 60 s, never gives
  up), then calls `BleRelay.rebind_central()` to resubscribe on the new link.
  The peripheral is deliberately untouched, so the consumer keeps its
  connection and its CCCDs and just sees a gap in the stream. The read cache
  is kept too — it holds erg identity, which does not change when the link
  does. `reconnects` counts them.
- `unavailable_characteristics` became a per-pass gauge rather than a running
  total, or a reconnect would report a firmware gap that grows without bound.
- **R-OPS-3.** A poll of the peripheral adapter's `Device1.Connected` logs
  consumer connects and disconnects, and re-registers the advertisement on the
  disconnect edge. Note that whether BlueZ already resumes advertising on its
  own was **never actually established** — the §8 "disappeared from the app's
  scan" was confounded by the phone silently reattaching a bond, which §14.1
  removes. Re-registering makes it true either way; the new log settles the
  question on the next run.

Only the first connect still fails fast ("No PM5 found — wake it with the
handle"): an erg asleep at startup is a setup mistake worth reporting, whereas
a mid-session drop is worth riding out.

### 14.5 Second 2026-09-06 hardware run — latency root cause + SIGINT defect

Hardware session on edge-04 (`<PI-IP-REDACTED>`) exercising the §14.1/§14.4
fixes against the real PM5 and the Concept2 app.

**Write payload logging** (`ace886b`, prerequisite for the below): an
over-length consumer write only ever logged the length, not the bytes —
insufficient to design a translation. The relay now logs the hex payload too,
on the anomaly path only, so it stays off the hot path.

**Root cause of the ~1 s latency, confirmed** (`12a4e62`): the app writes
`02 00 00 00 00 00 00 00` to `ce060034` — a little-endian 64-bit `2`, i.e. a
request for a 250 ms sample rate — into a characteristic the spec (and the
real PM5) declares as **1 byte**. A phone connected directly to the erg is
constrained to 1 byte before the write goes out; the emulated server did not
enforce that limit, so all 8 bytes were forwarded whole as an ATT Write
Request, and the PM5 answered **Invalid Attribute Value Length (`0x0D`)** and
discarded it. The erg stayed at its 1 Hz default for the entire session while
the app believed it had asked for 250 ms — this is essentially the whole ~1 s
gap versus a direct connection, confirming hypothesis 1 from §14.2 outright.

The relay's own forward path measures **1.2 ms mean / 4.2 ms max** — the
30–100 ms estimate in §11.1's table was never real; the entire visible cost
was the rejected write forcing the PM5 back to its slow default.

**Fix:** truncate an over-length consumer write to the characteristic's
declared length before forwarding, reproducing the real erg's own contract at
the ATT layer. This is not a relay-side rate policy — the app's chosen value
(`2` = 250 ms) passes through unchanged, only the length is clamped — so it is
consistent with the spirit of R-LATENCY-1, but the literal wording ("forward
these writes intact") is now wrong and needed revising (done below).

**SIGINT/SIGTERM defect, found and fixed in the same session** (`aad17bf`):
the documented `pkill -INT` stop procedure had never actually worked. The
relay relied on `KeyboardInterrupt`, which does nothing when the process has
no controlling terminal (it was started under `setsid`, per §8) — SIGINT was
silently ignored, five more stats intervals ran, and the `finally` block
(which disconnects the PM5) never fired. SIGTERM was not handled at all
either, so systemd would have killed the process mid-session with the same
effect. Every prior "clean" stop in this log actually left the PM5 connected
on `hci0`, which is why the next run's scan sometimes failed to find it (§8).
Fixed with explicit `asyncio` signal handlers for both signals, and the
reconnect loop moved into a separate supervisor task so the main coroutine
just waits on the stop event; the central disconnect in the shutdown path now
logs an error (not `contextlib.suppress`) if it fails, since a missed
disconnect stalls the *next* run, not just this one.

**Not yet re-run:** the `forward_ms`/`notifications_withheld`/subscribe-line
capture this section's predecessor asked for — the write-payload finding
resolved hypothesis 1 before that instrumentation was needed for its
originally intended purpose. It remains in place for the `c2m-ooz.3.3`
end-to-end session and is still useful there (e.g. to catch any *other*
over-length write from the app).

**Still unverified, because it needs the full loop through the app:** that
raising the erg's actual notification rate (now that its write reaches the
PM5 undamaged) closes the perceived lag to something comparable to the
~0.15 s direct baseline, and that no other characteristic hits the same
over-length pattern. Both are `c2m-ooz.3.3` work.
