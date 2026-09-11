---
status: Accepted
date: 2026-09-11
impact: high
tags: [architecture, mqtt, devices, di, testing]
---

# ADR-004: Pm5Port Hexagonal Architecture with cosalette

## Status

Accepted **Date:** 2026-09-11

## Context

concept2mqtt needs an application layer that wires the PM5 BLE connection to MQTT publishing. The PM5 communicates via Concept2's proprietary CSAFE-over-BLE protocol, decoded by the Rust csafe-codec library (ADR-002). The BLE relay subsystem (ADR-003) already owns the raw BLE connection; the application layer sits above it, consuming decoded telemetry and exposing it as MQTT topics.

Key constraints: (1) the PM5 adapter must be testable without real BLE hardware, requiring a clean port/adapter boundary; (2) cosalette (v0.9.6) is available as an opinionated IoT-to-MQTT framework providing App, Router, DI, MQTT wiring, health/LWT, and testing infrastructure; (3) the csafe-codec exposes PyO3-generated domain types (GeneralStatus, StrokeData, etc.) that represent wire-format data, not application-domain concepts; (4) only one device type (PM5) exists today, but the architecture should not preclude future device types.

The Pm5Port Protocol defines the domain-level contract between the application (cosalette device handlers) and the PM5 hardware adapter. It must speak in domain types (identity, workout state, stroke metrics) rather than raw BLE bytes or CSAFE wire formats, so that device handlers and tests never depend on transport details.

## Decision

Use cosalette as the application framework with a hexagonal Pm5Port Protocol defining the domain boundary between device handlers and the PM5 adapter, because cosalette provides the MQTT wiring, health/LWT, DI, and testing infrastructure the application needs, and the Protocol pattern (already proven in the BLE relay subsystem) cleanly separates domain logic from BLE transport, enabling a FakePm5Adapter test double that exercises the full device handler without hardware.

```python
from typing import Protocol
from cosalette import App, DeviceContext

class Pm5Port(Protocol):
    """Domain-level interface to a PM5 rowing monitor."""
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def identity(self) -> Pm5Identity: ...
    def events(self) -> AsyncIterator[Pm5Event]: ...

app = App("concept2mqtt", adapters={Pm5Port: BleakPm5Adapter})

@app.device("pm5")
async def pm5_device(ctx: DeviceContext) -> AsyncIterator[None]:
    pm5 = ctx.adapter(Pm5Port)
    await pm5.connect()
    try:
        ident = await pm5.identity()
        await ctx.publish_state({"serial": ident.serial_number})
        yield  # complete framework startup before consuming events
        async for event in pm5.events():
            # publish event
            yield
    finally:
        await pm5.disconnect()
```

## Decision Drivers

- The PM5 adapter must be testable without real BLE hardware — a clean port boundary enables FakePm5Adapter
- cosalette provides MQTT wiring, health/LWT, DI (ctx.adapter), and testing infrastructure (AppHarness) that would otherwise need to be built from scratch
- The BLE relay subsystem already uses Protocol classes (CentralLink, PeripheralServer) successfully — the same pattern at the domain level maintains consistency
- csafe-codec's PyO3-generated types represent wire format, not domain concepts — a port boundary prevents wire-format leakage into device handlers
- Only one device type (PM5) exists today, but cosalette's Router pattern supports future devices without architectural changes

## Considered Options

### Option 1: cosalette + hexagonal Pm5Port Protocol (chosen)

Use cosalette as the application framework. Define Pm5Port as a typing.Protocol specifying domain-level operations (connect, disconnect, identity, and events). Register adapters via cosalette's DI (App(adapters={Pm5Port: BleakPm5Adapter})). Device handlers use ctx.adapter(Pm5Port) to obtain the adapter. A FakePm5Adapter test double implements Pm5Port with canned responses for use with cosalette's AppHarness.

- *Advantages:* Clean domain boundary — device handlers never see BLE bytes, GATT UUIDs, or CSAFE wire format; Proven pattern — CentralLink and PeripheralServer Protocols in the BLE relay subsystem demonstrate the approach works well in this codebase; Full testing without hardware — FakePm5Adapter + AppHarness enables end-to-end device handler tests; cosalette handles MQTT connection, reconnection, LWT, health, structured logging, and CLI — zero custom infrastructure code; cosalette's DI resolves Pm5Port to the registered adapter automatically, reducing wiring boilerplate
- *Disadvantages:* Adds a framework dependency (cosalette) that constrains application structure; Domain types (Pm5Identity, Pm5Status, etc.) must be defined as thin wrappers over csafe-codec types, adding a mapping layer; Requires Python >= 3.14, narrowing the deployment environment

### Option 2: Custom Application class with Pm5Port Protocol

Build a bespoke Application class that manages the PM5 adapter lifecycle, MQTT publishing, and health reporting directly. Define Pm5Port identically as a Protocol, but wire everything manually using asyncio and aiomqtt.

- *Advantages:* No framework dependency — full control over application structure; Simpler dependency tree; Can target Python >= 3.13
- *Disadvantages:* Must build MQTT connection management, reconnection, LWT, health reporting, structured logging, and CLI from scratch; Must build a testing harness from scratch (cosalette.testing.AppHarness provides this for free); No established DI mechanism — adapter wiring must be hand-rolled; Significant implementation effort for infrastructure that is not concept2mqtt's core value proposition

### Option 3: Direct integration without port abstraction

Wire the BLE adapter directly into MQTT publishing handlers with no Protocol boundary. Device handlers import and use bleak types directly, with the adapter embedded in the handler logic.

- *Advantages:* Fewest files and abstractions — no port, no domain types, no adapter mapping; Fastest initial implementation
- *Disadvantages:* Untestable without real BLE hardware — bleak types cannot be instantiated without a BLE connection; Wire-format details (GATT UUIDs, CSAFE byte sequences) leak into MQTT publishing code; Violates the hexagonal architecture principle already established in the BLE relay subsystem; Any change to the BLE transport layer forces changes in every device handler; No path to supporting alternative transports (e.g. USB-connected PM5) without rewriting handlers

## Decision Matrix

| Criterion | cosalette + hexagonal Pm5Port Protocol | Custom Application class with Pm5Port Protocol | Direct integration without port abstraction |
| --- | --- | --- | --- |
| Testability without hardware | 5 | 5 | 1 |
| Implementation effort (infrastructure) | 5 | 2 | 4 |
| Domain boundary clarity | 5 | 5 | 1 |
| Consistency with existing codebase patterns | 5 | 4 | 1 |
| Extensibility to future device types | 5 | 3 | 1 |
| Dependency footprint | 3 | 4 | 5 |

_Scale: 1 (poor) to 5 (excellent)_

## Consequences

### Positive

- Device handlers are fully testable via FakePm5Adapter + cosalette's AppHarness — no BLE hardware needed for CI
- MQTT wiring, reconnection, LWT, health, structured logging, and CLI are provided by cosalette — zero custom infrastructure code to maintain
- The Pm5Port Protocol establishes a stable domain contract that insulates device handlers from transport-layer changes
- The architecture is consistent with the BLE relay subsystem's Protocol-based design (CentralLink, PeripheralServer), maintaining a single architectural style across the codebase

### Negative

- cosalette becomes a load-bearing dependency — major version changes could require significant application-layer rewrites
- Python >= 3.14 requirement narrows the deployment environment (Raspberry Pi OS must provide 3.14+)
- Domain types (Pm5Identity, Pm5Status, etc.) create a thin mapping layer between csafe-codec wire types and application logic, adding files and translation code

_2026-09-11_
