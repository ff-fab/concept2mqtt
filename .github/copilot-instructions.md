# GitHub Copilot Instructions

## Project Overview

**concept2mqtt** — a Python bridge that connects a Concept2 PM5 rowing machine to MQTT
via BLE, built on the [cosalette](https://cosalette.dev) IoT-to-MQTT framework.

### Key Technical Context

- **PM5 CSAFE protocol spec** (Rev 0.25) is in `docs/planning/spec/csafe/` as
  machine-readable YAML (9 files, 10k+ lines). Use these as the source of truth for
  command IDs, data formats, enums, and BLE characteristics.
- **BLE base UUID**: `CE06XXXX-43E5-11E4-916C-0800200C9A66` (replace `XXXX`).
- **cosalette patterns**: `@app.device`, `@app.telemetry`, `@app.command` decorators.
  Hexagonal architecture with `Protocol` ports and adapters. See cosalette docs for
  the full-app guide and adapter patterns.
- **CSAFE codec** is a **Rust crate** (`packages/csafe-codec/`) exposed to Python via
  PyO3 + maturin. Pure library (no I/O) — frame/unframe, command builders, and
  notification decoders. Published to crates.io and PyPI. Must be 100% unit-testable
  with test vectors from the YAML spec.
- **Target hardware**: Raspberry Pi Zero 2 W (BLE 4.2 via BCM43436s, single-band
  2.4GHz WiFi). PM5 likely supports only 1 simultaneous BLE connection.
- **MQTT broker** runs on a separate machine (not on the Pi).

### Architecture

- **Option C**: High-level `Pm5Port` Protocol + standalone CSAFE codec library (Rust)
- `BleakPm5Adapter` implements `Pm5Port`, uses the Rust codec internally
- `FakePm5Adapter` for testing — canned domain-level responses, no BLE mocking

### Design Documents

- Feature plan: `docs/planning/feature-plan.md`
- Design sparring: `docs/planning/sparring-concept2mqtt-r2.md`
- ADRs: `docs/adr/`

## Workflow

- **Branching:** GitHub Flow — branch from `main`, open PR, squash-merge.
- **Commits:** Conventional Commits required (`feat:`, `fix:`, `docs:`, `chore:`, etc.).
- **Releases:** Automated via Release Please (SemVer tags).
- **Never push directly to `main`.**

## Pull Request & Merge Policy

**NEVER merge a pull request unless the user explicitly asks you to merge.**

Your job ends at creating the PR and waiting for CI. The human reviewer decides when to
merge. Even if all CI checks pass and the code looks perfect — do NOT merge. Do NOT
approve-and-merge. Do NOT enable auto-merge. Wait for an explicit user instruction like
"merge this", "go ahead and merge", or "land it".

## Code Quality Principles

- **Brevity is a feature.** If you wrote 200 lines and it could be 50, rewrite it.
- **Simplicity test:** Ask yourself — "Would a senior engineer say this is
  overcomplicated?" If yes, simplify before submitting.
- Prefer clear, idiomatic code over clever abstractions.
- Every line should earn its place — remove dead code, redundant comments, and
  unnecessary indirection.

## GitHub Operations

- Prefer **`gh` CLI** and **`git` CLI** for pull requests, reviews, comments, and issue operations.
- Do not depend on GitKraken MCP authentication in this repository.
- When multiple automation paths exist, choose `gh` commands first.

## Architecture Decision Records

All major decisions are documented in `docs/adr/`. **Follow these decisions.**

Create new ADRs for any major changes or decisions.
