"""BLE smoke test — connect to PM5 and read Device Information.

This is the Phase 1 smoke test from the PoC plan. It validates:
  1. BLE scanning finds a PM5 device
  2. Connection succeeds
  3. Device Information characteristics are readable (standard GATT read)
  4. Notification subscription works (Rowing General Status)
  5. Clean disconnect is attempted; transient disconnect races may be logged as
     warnings and do not on their own fail the test.

Run on the Pi via:  task pi:smoke

Pass criteria: Device Information read successfully, notification subscription OK;
clean disconnect is best-effort and WARN-only.
"""

import asyncio
import logging
import sys

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice

# ---------------------------------------------------------------------------
# PM5 BLE UUIDs
# ---------------------------------------------------------------------------
# Concept2 proprietary base: CE06xxxx-43E5-11E4-916C-0800200C9A66

# Device Information Service characteristics (support standard GATT reads)
UUID_SERIAL_NUMBER = "ce060012-43e5-11e4-916c-0800200c9a66"
UUID_HARDWARE_REV = "ce060013-43e5-11e4-916c-0800200c9a66"
UUID_FIRMWARE_REV = "ce060014-43e5-11e4-916c-0800200c9a66"
UUID_MANUFACTURER = "ce060015-43e5-11e4-916c-0800200c9a66"

# Rowing Primary Service — notification-only characteristics
UUID_ROWING_GENERAL_STATUS = "ce060031-43e5-11e4-916c-0800200c9a66"
UUID_ROWING_ADDITIONAL_STATUS_1 = "ce060032-43e5-11e4-916c-0800200c9a66"

# PM5 device name prefix used for scanning
PM5_NAME_PREFIX = "PM5"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("smoke_ble")


# ---------------------------------------------------------------------------
# Step 1: Scan for PM5
# ---------------------------------------------------------------------------
async def find_pm5(timeout: float = 15.0) -> BLEDevice | None:
    """Scan for a PM5 device by name prefix."""
    log.info("Scanning for PM5 devices (%ss)...", timeout)
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
    log.warning("  No PM5 found among %d devices", len(devices))
    return None


# ---------------------------------------------------------------------------
# Step 2: Read Device Information
# ---------------------------------------------------------------------------
async def read_device_info(client: BleakClient) -> dict[str, str]:
    """Read Device Information Service characteristics (standard GATT read)."""
    info: dict[str, str] = {}
    char_map = {
        "serial_number": UUID_SERIAL_NUMBER,
        "hardware_rev": UUID_HARDWARE_REV,
        "firmware_rev": UUID_FIRMWARE_REV,
        "manufacturer": UUID_MANUFACTURER,
    }
    for name, char_uuid in char_map.items():
        try:
            raw = await client.read_gatt_char(char_uuid)
            info[name] = raw.decode("utf-8", errors="replace").strip()
            log.info("  %s: %s", name, info[name])
        except Exception as exc:
            log.error("  %s: FAILED (%s)", name, exc)
            info[name] = f"ERROR: {exc}"
    return info


# ---------------------------------------------------------------------------
# Step 3: Subscribe to notifications briefly
# ---------------------------------------------------------------------------
async def test_notifications(client: BleakClient, duration: float = 5.0) -> int:
    """Subscribe to Rowing General Status and count notifications received."""
    received: list[bytes] = []

    def on_notify(_sender: BleakGATTCharacteristic, data: bytearray) -> None:
        received.append(bytes(data))
        log.info("  Notification #%d: %d bytes", len(received), len(data))

    log.info("Subscribing to Rowing General Status notifications (%ss)...", duration)
    await client.start_notify(UUID_ROWING_GENERAL_STATUS, on_notify)
    await asyncio.sleep(duration)
    await client.stop_notify(UUID_ROWING_GENERAL_STATUS)

    count = len(received)
    if count > 0:
        log.info("  Received %d notifications", count)
    else:
        log.info("  No notifications received (PM5 may be idle — this is OK)")
    return count


# ---------------------------------------------------------------------------
# Main smoke test
# ---------------------------------------------------------------------------
def _handle_ble_error(results: dict[str, str], exc: Exception) -> None:
    """Classify a BLE exception and update results accordingly.

    If all post-connect checks completed, the error is likely a benign disconnect
    race and is recorded as WARN. Otherwise, incomplete steps are marked FAIL.
    """
    if results.get("connect") != "PASS":
        log.error("Connection failed: %s", exc)
        results["connect"] = f"FAIL ({exc})"
        return

    all_checks_done = all(key in results for key in ("device_info", "notifications"))
    if all_checks_done:
        log.warning("Disconnect issue (non-critical): %s", exc)
        results["disconnect"] = f"WARN ({exc})" if str(exc) else "WARN"
    else:
        log.error("Error during BLE smoke test after connect: %s", exc)
        if "device_info" not in results:
            results["device_info"] = f"FAIL ({exc})"
        if "notifications" not in results:
            results["notifications"] = f"FAIL ({exc})"
        results["disconnect"] = f"FAIL ({exc})"


async def smoke_test() -> bool:
    """Run the full BLE smoke test. Returns True if all critical checks pass."""
    results: dict[str, str] = {}

    # --- Scan ---
    pm5 = await find_pm5()
    if pm5 is None:
        results["scan"] = "FAIL"
        _print_summary(results)
        return False
    results["scan"] = "PASS"

    # --- Connect & test ---
    log.info("Connecting to %s (%s)...", pm5.name, pm5.address)
    try:
        async with BleakClient(pm5, timeout=20.0) as client:
            log.info("Connected: %s", client.is_connected)
            results["connect"] = "PASS"

            # Device Information (standard GATT read — this SHOULD work on PM5)
            log.info("Reading Device Information...")
            info = await read_device_info(client)
            serial_number = info.get("serial_number")
            has_serial = isinstance(
                serial_number, str
            ) and not serial_number.startswith("ERROR:")
            results["device_info"] = "PASS" if has_serial else "FAIL"

            # Notifications
            notification_count = await test_notifications(client, duration=5.0)
            # Notifications are informational — PM5 only sends them during a workout
            # or in certain states. Not receiving any when idle is expected.
            results["notifications"] = (
                f"PASS ({notification_count} received)"
                if notification_count > 0
                else "INFO (0 received — PM5 likely idle, subscription OK)"
            )

        # If we get here, disconnect was clean (context manager handles it)
        results["disconnect"] = "PASS"

    except Exception as exc:
        _handle_ble_error(results, exc)

    _print_summary(results)
    return all("FAIL" not in v for v in results.values())


def _print_summary(results: dict[str, str]) -> None:
    """Print a pass/fail summary table."""
    print("\n" + "=" * 60)
    print("BLE SMOKE TEST SUMMARY")
    print("=" * 60)
    for check, status in results.items():
        marker = "✓" if "FAIL" not in status else "✗"
        print(f"  {marker} {check:20s} {status}")
    all_pass = all("FAIL" not in v for v in results.values())
    print("=" * 60)
    print(f"  {'PASSED' if all_pass else 'FAILED'}")
    print("=" * 60 + "\n")


def main() -> None:
    """Entry point."""
    success = asyncio.run(smoke_test())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
