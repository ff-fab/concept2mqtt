"""Quick BLE scan — discover nearby devices, highlight PM5s.

Run on the Pi via:  task pi:scan
"""

import asyncio

from bleak import BleakScanner


async def scan(timeout: float = 10.0) -> None:
    """Scan for BLE devices and print a sorted list."""
    print(f"Scanning for BLE devices ({timeout}s)...")
    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    for device, adv in sorted(devices.values(), key=lambda x: x[1].rssi, reverse=True):
        pm5 = " <<< PM5" if device.name and "PM5" in device.name else ""
        name = device.name or "(unknown)"
        print(f"  {device.address}  RSSI={adv.rssi:4d}  {name}{pm5}")

    if not devices:
        print("  No devices found.")
    else:
        print(f"\n{len(devices)} devices found.")


def main() -> None:
    """Entry point."""
    asyncio.run(scan())


if __name__ == "__main__":
    main()
