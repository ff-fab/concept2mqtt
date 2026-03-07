"""PM5 dual BLE connection proof-of-concept.

Validates whether the PM5 can maintain two simultaneous BLE connections.
Run this on the Pi while the Concept2 app is connected on an iPhone.

Test matrix:
  Phase 1: Scan — can Pi see PM5 while iPhone is connected?
  Phase 2: Connect — can Pi establish a second BLE connection?
  Phase 3: GATT read — can Pi read device info with both connected?
  Phase 4: Notifications — does Pi receive rowing status notifications?
  Phase 5: Manual check — is the iPhone Concept2 app still connected?

Prerequisites:
  - PM5 powered on (pull handle or press button to wake)
  - iPhone Concept2 app connected to PM5
  - Pi in BLE range of PM5 (~5m or less)

Run:  uv run python docs/planning/legacy/examples/test_dual_ble.py

Pass criteria:
  - If Pi connects successfully → dual connection is possible
  - If Pi fails to connect → PM5 supports only 1 BLE connection
  - Both outcomes are useful for architecture planning
"""

import asyncio
import logging
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("dual_ble")


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
            log.info(
                "  Press Enter after checking"
                " (or type 'dropped' if iPhone lost connection)"
            )
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, input, "  > "
            )
            if "drop" in user_input.lower():
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
        marker = "✓" if "FAIL" not in status else "✗"
        print(f"  {marker} {check:25s} {status}")
    print("=" * 70)

    # Architecture conclusion
    connect_result = results.get("connect", "")
    if "PASS" in connect_result:
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
    input("Press Enter when ready...")
    print()

    # Phase 1: Scan
    pm5 = await phase_scan()
    if pm5 is None:
        results["scan"] = "FAIL — PM5 not found"
        print_summary(results)
        return False
    results["scan"] = f"PASS — {pm5.name} ({pm5.address})"

    # Phase 2-5: Connect and test
    test_results = await phase_connect_and_test(pm5)
    results.update(test_results)

    print_summary(results)
    return all("FAIL" not in v for v in results.values())


def entry_point() -> None:
    """Entry point."""
    success = asyncio.run(main())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    entry_point()
