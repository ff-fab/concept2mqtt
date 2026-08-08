"""PM5 dual BLE connection proof-of-concept.

Validates whether the PM5 can maintain two simultaneous BLE connections.
Run this on the Pi while the Concept2 app is connected on an iPhone.

Test matrix:
  Phase 1: Scan — can Pi see PM5 while iPhone is connected?
  Phase 1b: Bonded fallback — if Phase 1 fails, does a *known* (bonded) device
    fare any better? The PM5 stops advertising once any BLE central holds a
    connection, so a fresh scan can never find it in that state — bonding once
    beforehand gives BlueZ a persistent device object that doesn't depend on
    seeing a live advertisement. bleak's own connect-by-address still performs
    an internal scan-based lookup even for bonded devices, so this fallback
    shells out to `bluetoothctl connect` (BlueZ D-Bus, Linux-only) to attempt
    the actual link-layer connection directly.
  Phase 2: Connect — can Pi establish a second BLE connection?
  Phase 3: GATT read — can Pi read device info with both connected?
  Phase 4: Notifications — does Pi receive rowing status notifications?
  Phase 5: Manual check — is the iPhone Concept2 app still connected?

Prerequisites:
  - PM5 powered on (pull handle or press button to wake)
  - iPhone Concept2 app connected to PM5
  - Pi in BLE range of PM5 (~5m or less)
  - For the Phase 1b fallback to have anything to work with, the PM5 must have
    been paired/bonded to this Pi at least once beforehand (while it was still
    advertising, i.e. before the iPhone connects):
      bluetoothctl
      > agent NoInputNoOutput
      > default-agent
      > scan on
      > pair <PM5 MAC>
      > trust <PM5 MAC>

Run:  uv run python docs/planning/legacy/examples/test_dual_ble.py

When stdin is not a TTY (e.g. invoked over a non-interactive SSH exec), the two
manual checkpoints (start confirmation, iPhone coexistence check) are skipped
automatically instead of blocking forever; the iPhone check is then reported as
MANUAL and must be verified separately.

Pass criteria:
  - If Pi connects successfully → dual connection is possible
  - If Pi fails to connect (Phase 2, or the Phase 1b fallback) → PM5 supports
    only 1 BLE connection
  - Both outcomes are useful for architecture planning
"""

import asyncio
import logging
import re
import subprocess
import sys
import time

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice

# ---------------------------------------------------------------------------
# PM5 BLE UUIDs (Concept2 base: CE06XXXX-43E5-11E4-916C-0800200C9A66)
# ---------------------------------------------------------------------------
UUID_SERIAL_NUMBER = "ce060012-43e5-11e4-916c-0800200c9a66"
UUID_HARDWARE_REV = "ce060013-43e5-11e4-916c-0800200c9a66"
UUID_FIRMWARE_REV = "ce060014-43e5-11e4-916c-0800200c9a66"
UUID_MANUFACTURER = "ce060015-43e5-11e4-916c-0800200c9a66"
UUID_ROWING_GENERAL_STATUS = "ce060031-43e5-11e4-916c-0800200c9a66"
UUID_ROWING_ADDITIONAL_STATUS_1 = "ce060032-43e5-11e4-916c-0800200c9a66"

PM5_NAME_PREFIX = "PM5"
NOTIFICATION_DURATION = 10.0  # seconds to listen for notifications
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("dual_ble")


async def _prompt(message: str) -> str | None:
    """Prompt for input, or return None immediately when stdin isn't a TTY."""
    if not sys.stdin.isatty():
        log.info("  (non-interactive session — skipping prompt)")
        return None
    return await asyncio.get_event_loop().run_in_executor(None, input, message)


# ---------------------------------------------------------------------------
# Phase 1: Scan for PM5
# ---------------------------------------------------------------------------
async def phase_scan(timeout: float = 15.0) -> BLEDevice | None:
    """Scan for PM5 while iPhone may hold an active connection."""
    log.info("PHASE 1: Scanning for PM5 (%ss)...", timeout)
    log.info("  (iPhone Concept2 app should be connected already)")

    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    for device, adv in devices.values():
        if device.name and PM5_NAME_PREFIX in device.name:
            log.info(
                "  Found: %s (%s, RSSI=%s)",
                device.name,
                device.address,
                adv.rssi,
            )
            return device

    log.warning("  PM5 not found among %d devices", len(devices))
    log.info("  Possible reasons:")
    log.info("    - PM5 is in deep sleep (pull handle to wake)")
    log.info("    - PM5 stops advertising when a connection is active")
    log.info("    - PM5 is out of BLE range")
    return None


# ---------------------------------------------------------------------------
# Phase 1b: Bonded fallback (Linux/BlueZ only)
# ---------------------------------------------------------------------------
def find_bonded_pm5_address() -> str | None:
    """Look up an already-bonded PM5's address via `bluetoothctl`.

    A device only needs to be paired/bonded once (while it was still
    advertising) for BlueZ to keep a persistent object for it. Returns None if
    `bluetoothctl` is unavailable or no bonded PM5 is found.
    """
    try:
        result = subprocess.run(
            ["bluetoothctl", "devices", "Paired"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
        log.debug("  bluetoothctl lookup failed: %s", exc)
        return None

    for line in result.stdout.splitlines():
        # Format: "Device XX:XX:XX:XX:XX:XX Some Name"
        parts = line.split(maxsplit=2)
        if len(parts) == 3 and parts[0] == "Device" and PM5_NAME_PREFIX in parts[2]:
            return parts[1]
    return None


async def is_pm5_advertising(timeout: float = 6.0) -> bool:
    """Quick scan to check whether the PM5 is currently advertising.

    Used to bracket the bonded-connect attempt: if the PM5 is advertising, no
    central currently holds a connection to it, so any "successful" bonded
    connect wouldn't actually prove dual-connection support — it just found an
    unoccupied PM5. A false PASS was observed in practice when the iPhone's
    connection silently dropped (screen lock) between test setup and the
    connect attempt.
    """
    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    return any(d.name and PM5_NAME_PREFIX in d.name for d, _ in devices.values())


def bluetoothctl_connect(address: str, timeout: float = 45.0) -> tuple[bool, str]:
    """Attempt a real link-layer connect via `bluetoothctl` to a bonded device.

    Unlike bleak's connect-by-address (which still performs an internal
    scan-based lookup and gives up early if the device isn't currently
    advertising), `bluetoothctl connect` targets BlueZ's persistent bonded
    device object directly, so it actually exercises the link-layer connection
    attempt even when the peer has stopped advertising. Disconnects again
    immediately on success to leave the adapter in a clean state.
    """
    try:
        result = subprocess.run(
            ["bluetoothctl", "connect", address],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout:.0f}s (no response from adapter)"
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
        return False, f"bluetoothctl unavailable ({exc})"

    output = (result.stdout + result.stderr).strip()
    detail = _summarize_bluetoothctl_output(output)
    if "Connection successful" in output or "Connected: yes" in output:
        subprocess.run(
            ["bluetoothctl", "disconnect", address],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True, detail
    return False, detail


def _summarize_bluetoothctl_output(raw: str) -> str:
    """Reduce raw bluetoothctl chatter to just the meaningful result line.

    bluetoothctl's non-interactive output is full of ANSI colour codes and
    unrelated device-discovery churn ([NEW]/[DEL]/[CHG] lines for every other
    BLE device in range). Only the final substantive line — usually
    "Failed to connect: ..." or "Connection successful" — is useful to record.
    """
    cleaned = _ANSI_ESCAPE_RE.sub("", raw)
    lines = [
        line.strip()
        for line in cleaned.splitlines()
        if line.strip() and not line.strip().startswith(("[NEW]", "[DEL]", "[CHG]"))
    ]
    return lines[-1] if lines else cleaned.strip()


async def phase_bonded_fallback() -> dict[str, str]:
    """Fallback when Phase 1's scan can't see the PM5 (it isn't advertising).

    Checks for a bonded PM5 and attempts a direct link-layer connect via
    `bluetoothctl`. This can only report connect/reject — bleak still can't
    attach for GATT reads or notifications without a live advertisement, so
    Phases 3/4 are skipped when this path is taken.
    """
    log.info("PHASE 1b: PM5 not advertising — trying bonded-device fallback...")
    address = find_bonded_pm5_address()
    if address is None:
        log.info("  No bonded PM5 found (bluetoothctl unavailable, or PM5 was")
        log.info("  never paired while it was still advertising). Skipping.")
        return {}

    log.info("  Found bonded PM5 at %s — attempting direct connect...", address)
    log.info("  (this is the real test: does the link layer accept a 2nd")
    log.info("  connection, independent of advertising/discovery?)")
    t0 = time.monotonic()
    success, detail = bluetoothctl_connect(address)
    elapsed = time.monotonic() - t0

    # Bracket check: confirm the PM5 was still occupied (not advertising) right
    # after the attempt too, so a mid-test drop of the *other* connection can't
    # be mistaken for evidence about dual-connection support either way.
    log.info("  Bracket check: is PM5 advertising again right now?")
    reappeared = await is_pm5_advertising()

    if success:
        if reappeared:
            log.warning(
                "  Connected in %.1fs, but PM5 is advertising again — the other"
                " connection may have dropped during the test. INCONCLUSIVE.",
                elapsed,
            )
            return {
                "connect": (
                    f"INCONCLUSIVE — bonded connect PASS in {elapsed:.1f}s, but"
                    " PM5 re-advertised after (other connection may have"
                    " dropped mid-test — verify it stayed connected throughout)"
                ),
            }
        log.info("  Connected in %.1fs via bluetoothctl — dual BLE works!", elapsed)
        return {
            "connect": f"PASS — bonded connect in {elapsed:.1f}s (bluetoothctl)",
            "gatt_reads": "SKIPPED — bleak can't attach without a scan hit",
            "notifications": "SKIPPED — bleak can't attach without a scan hit",
        }

    log.error("  Bonded connect failed after %.1fs: %s", elapsed, detail)
    if reappeared:
        log.warning(
            "  PM5 is advertising again — the other connection may have"
            " dropped independently. This failure is INCONCLUSIVE."
        )
        return {
            "connect": (
                f"INCONCLUSIVE — bonded connect FAILED ({detail}), and PM5"
                " re-advertised after (other connection may have dropped"
                " independently — retest with the other side confirmed stable)"
            ),
        }
    log.info("  Confirmed: PM5 still not advertising — the other connection")
    log.info("  held throughout, so this failure is a real rejection.")
    log.info("")
    log.info("  This means PM5 supports only 1 BLE connection — the link layer")
    log.info("  itself refuses/ignores a 2nd central, even when already bonded.")
    log.info("  Architecture implication: concept2mqtt = sole BLE gateway.")
    return {"connect": f"FAIL — bonded connect rejected ({detail})"}


# ---------------------------------------------------------------------------
# Phase 2+3+4: Connect, read, subscribe
# ---------------------------------------------------------------------------
async def phase_connect_and_test(
    pm5: BLEDevice,
) -> dict[str, str]:
    """Attempt to connect and run all tests."""
    results: dict[str, str] = {}

    log.info("PHASE 2: Connecting to %s (%s)...", pm5.name, pm5.address)
    log.info("  (This is the critical test — can a 2nd connection coexist?)")

    t0 = time.monotonic()
    try:
        async with BleakClient(pm5, timeout=20.0) as client:
            elapsed = time.monotonic() - t0
            log.info("  Connected in %.1fs — dual BLE connection works!", elapsed)
            results["connect"] = f"PASS — connected in {elapsed:.1f}s"

            # Phase 3: GATT reads
            log.info("PHASE 3: Reading device info (GATT read)...")
            char_map = {
                "serial_number": UUID_SERIAL_NUMBER,
                "hardware_rev": UUID_HARDWARE_REV,
                "firmware_rev": UUID_FIRMWARE_REV,
                "manufacturer": UUID_MANUFACTURER,
            }
            for name, uuid in char_map.items():
                try:
                    raw = await client.read_gatt_char(uuid)
                    value = raw.decode("utf-8", errors="replace").strip()
                    log.info("  %s: %s", name, value)
                    results[f"gatt_{name}"] = f"PASS — {value}"
                except Exception as exc:
                    log.error("  %s: FAILED (%s)", name, exc)
                    results[f"gatt_{name}"] = f"FAIL — {exc}"

            # Phase 4: Notifications
            log.info(
                "PHASE 4: Subscribing to notifications (%ss)...",
                NOTIFICATION_DURATION,
            )
            log.info("  (Start rowing or pull handle for notifications)")

            general_count = 0
            additional_count = 0

            def on_general(_: BleakGATTCharacteristic, data: bytearray) -> None:
                nonlocal general_count
                general_count += 1
                if general_count <= 3:
                    log.info(
                        "  General status #%d: %d bytes — %s",
                        general_count,
                        len(data),
                        data.hex(),
                    )

            def on_additional(_: BleakGATTCharacteristic, data: bytearray) -> None:
                nonlocal additional_count
                additional_count += 1
                if additional_count <= 3:
                    log.info(
                        "  Additional status #%d: %d bytes — %s",
                        additional_count,
                        len(data),
                        data.hex(),
                    )

            try:
                await client.start_notify(UUID_ROWING_GENERAL_STATUS, on_general)
                await client.start_notify(
                    UUID_ROWING_ADDITIONAL_STATUS_1, on_additional
                )
                await asyncio.sleep(NOTIFICATION_DURATION)
                await client.stop_notify(UUID_ROWING_GENERAL_STATUS)
                await client.stop_notify(UUID_ROWING_ADDITIONAL_STATUS_1)
            except Exception as exc:
                log.warning("  Notification error: %s", exc)

            log.info(
                "  Received: %d general, %d additional status notifications",
                general_count,
                additional_count,
            )
            total = general_count + additional_count
            results["notifications"] = (
                f"PASS — {total} received ({general_count} general, "
                f"{additional_count} additional)"
                if total > 0
                else "INFO — 0 received (PM5 may be idle; subscription OK)"
            )

            # Phase 5: Manual iPhone check
            log.info("")
            log.info("PHASE 5: Manual verification needed")
            log.info("  → Check your iPhone: is the Concept2 app still connected?")
            log.info("  → Does the app still show PM5 data?")
            log.info("")
            user_input = await _prompt(
                "  Press Enter after checking"
                " (or type 'dropped' if iPhone lost connection) > "
            )
            if user_input is None:
                results["iphone_coexistence"] = (
                    "MANUAL — not verified in this run (non-interactive session)"
                )
            elif "drop" in user_input.lower():
                results["iphone_coexistence"] = "FAIL — iPhone connection was dropped"
                log.warning("  iPhone lost connection when Pi connected")
            else:
                results["iphone_coexistence"] = "PASS — both connections coexisted"
                log.info("  Both connections coexisted — dual BLE confirmed!")

        results["disconnect"] = "PASS — clean disconnect"

    except Exception as exc:
        elapsed = time.monotonic() - t0
        log.error("  Connection failed after %.1fs: %s", elapsed, exc)
        results["connect"] = f"FAIL — {exc}"
        log.info("")
        log.info("  This likely means PM5 supports only 1 BLE connection.")
        log.info("  Architecture implication: concept2mqtt = sole BLE gateway.")

    return results


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def print_summary(results: dict[str, str]) -> None:
    """Print a clear pass/fail summary table."""
    print("\n" + "=" * 70)
    print("PM5 DUAL BLE CONNECTION TEST RESULTS")
    print("=" * 70)
    for check, status in results.items():
        if "INCONCLUSIVE" in status:
            marker = "?"
        elif "FAIL" in status:
            marker = "✗"
        else:
            marker = "✓"
        print(f"  {marker} {check:25s} {status}")
    print("=" * 70)

    # Architecture conclusion
    connect_result = results.get("connect", "")
    if "INCONCLUSIVE" in connect_result:
        print("\n  CONCLUSION: Inconclusive — retest with both sides confirmed")
        print("  stable throughout (see the 'connect' result above for why).")
    elif "PASS" in connect_result:
        print("\n  CONCLUSION: PM5 supports dual BLE connections.")
        print("  → concept2mqtt can coexist with phone apps.")
        print("  → Coaching app has the option of direct BLE OR MQTT relay.")
    elif "FAIL" in connect_result:
        print("\n  CONCLUSION: PM5 supports only 1 BLE connection.")
        print("  → concept2mqtt is the sole BLE gateway (architecture confirmed).")
        print("  → Coaching app MUST use MQTT relay via concept2mqtt.")
    else:
        scan_result = results.get("scan", "")
        if "FAIL" in scan_result:
            print("\n  CONCLUSION: PM5 not found during scan.")
            print("  → PM5 may stop advertising when a connection is active.")
            print("  → This itself suggests single-connection behaviour.")
            print("  → Retry with PM5 awake and no iPhone connection to verify.")

    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> bool:
    """Run the dual BLE connection proof-of-concept."""
    results: dict[str, str] = {}

    print("=" * 70)
    print("PM5 DUAL BLE CONNECTION PROOF-OF-CONCEPT")
    print("=" * 70)
    print()
    print("This test validates whether the PM5 can maintain two BLE")
    print("connections simultaneously (Pi + iPhone Concept2 app).")
    print()
    print("Prerequisites:")
    print("  1. PM5 is powered on (pull handle or press button)")
    print("  2. iPhone Concept2 app is connected to PM5")
    print("  3. Pi is within BLE range (~5m)")
    print()
    await _prompt("Press Enter when ready...")
    print()

    # Phase 1: Scan
    pm5 = await phase_scan()
    if pm5 is None:
        results["scan"] = "FAIL — PM5 not found (not advertising)"
        results.update(await phase_bonded_fallback())
        print_summary(results)
        # "scan" is expected to fail here (that's why the fallback ran) — the
        # real answer is the fallback's "connect" result, not scan visibility.
        connect_result = results.get("connect", "")
        return "PASS" in connect_result and "INCONCLUSIVE" not in connect_result
    results["scan"] = f"PASS — {pm5.name} ({pm5.address})"

    # Phase 2-5: Connect and test
    test_results = await phase_connect_and_test(pm5)
    results.update(test_results)

    print_summary(results)
    return all("FAIL" not in v and "INCONCLUSIVE" not in v for v in results.values())


def entry_point() -> None:
    """Entry point."""
    success = asyncio.run(main())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    entry_point()
