## Epic BLE Gateway: PM5 Peripheral Relay (c2m-ooz.3) — Software Phase Complete

Implemented the transport-free core of the BLE peripheral relay: a declarative
GATT profile model covering all five Concept2 proprietary services (plus an
UNVERIFIED FTMS profile behind a registry swap point), and a `BleRelay` that
moves opaque bytes between the sole PM5 connection and an emulated PM5 GATT
server. The BlueZ/D-Bus binding ships as a hardware PoC script rather than
production code, because none of it can be exercised without a Pi, a real PM5,
a second adapter and an iPhone.

**Files created/changed:**

- `packages/concept2mqtt/src/concept2mqtt/ble/__init__.py`
- `packages/concept2mqtt/src/concept2mqtt/ble/errors.py`
- `packages/concept2mqtt/src/concept2mqtt/ble/profile.py`
- `packages/concept2mqtt/src/concept2mqtt/ble/relay.py`
- `packages/concept2mqtt/tests/fixtures/ble.py`
- `packages/concept2mqtt/tests/unit/ble/test_profile.py`
- `packages/concept2mqtt/tests/unit/ble/test_profile_spec_conformance.py`
- `packages/concept2mqtt/tests/unit/ble/test_relay.py`
- `docs/planning/legacy/examples/relay_pm5.py`
- `docs/testing/pm5-ble-relay-hardware-validation.md`

**Functions/classes created/changed:**

- `pm5_uuid` / `sig_uuid` — 16-bit suffix to 128-bit UUID expansion
- `CharProperty`, `Characteristic`, `Service`, `GattProfile` — profile model
- `pm5_proprietary_profile`, `ftms_profile`, `get_profile`, `profile_names` —
  registry; the swap point for the unresolved proprietary-vs-FTMS question
- `SPEC_PROPERTY_ADDITIONS` — the one declared deviation from the spec table
- `CentralLink`, `PeripheralServer` — Protocols isolating both transports
- `BleRelay`, `RelayStats` — relay core with firmware-variance tolerance,
  lazy read-through caching, and notification-failure isolation
- `BleRelayError` and subclasses — `UnknownProfileError`,
  `UnknownCharacteristicError`, `CharacteristicAccessError`
- `BleakCentralLink`, `BluezPeripheralServer` (PoC script only)

**Tests created/changed:**

- `TestUuidExpansion`, `TestCharacteristicProperties`, `TestGattProfileLookup`,
  `TestProfileRegistry`, `TestPm5ProprietaryProfile`
- `TestCharacteristicConformance`, `TestServiceCoverage`,
  `TestDeclaredDeviations` — cross-check the Python table against
  `docs/planning/spec/csafe/ble_services.yaml` at test time
- `TestLifecycle`, `TestFirmwareVarianceTolerance`, `TestNotificationRelay`,
  `TestNotificationTap`, `TestNotificationFailureIsolation`, `TestWriteRelay`,
  `TestReadRelay`, `TestCacheCoherence`
- `FakeCentralLink`, `FakePeripheralServer` — in-memory doubles, not mocks

**Quality gates:** 193 tests pass; `task lint`, `task typecheck` and
`task complexity` all clean.

**Open — hardware-dependent, cannot be verified in this environment:**

- BLE traffic capture confirming which GATT service the iPhone app queries
- Feature neutrality of the app through the relay vs. a direct connection
- Extended-session stability against a real PM5
- Known-gap documentation, which depends on the two above

`c2m-ooz.3` stays open pending those. Procedure:
`docs/testing/pm5-ble-relay-hardware-validation.md`.

**Git Commit Message:**

```
feat: add BLE peripheral relay core and PM5 GATT profiles

- Add declarative GATT profile model with proprietary and FTMS profiles
- Add transport-free BleRelay over CentralLink/PeripheralServer protocols
- Add spec-conformance tests against ble_services.yaml
- Add hardware PoC script and manual validation procedure
```
