---
name: csafe-codec Rust/PyO3 package architecture
description:
  Module structure of packages/csafe-codec — Rust source, PyO3 bindings, Python shim
type: project
---

Package lives at `packages/csafe-codec/`. Key structure:

- `src/lib.rs` — PyO3 module root (`_native`), registers all functions/classes
- `src/ble/mod.rs` — 14 BLE decoder structs + `decode_*` functions +
  `decode_multiplexed`
- `src/ble/tests.rs` — Rust-level unit tests for BLE decoders
- `src/py_ble_decoders.rs` — PyO3 wrappers via `py_ble_decoder!` macro
- `src/commands/` — public.rs, proprietary.rs, types.rs, tests.rs
- `src/framing/` — byte stuffing, checksum, frame build/parse
- `src/response/` — CSAFE response parser
- `src/py_command_builders.rs`, `src/py_commands.rs`, `src/py_response.rs` — other PyO3
  wrappers
- `python/csafe_codec/` — Python shim with compiled `.so` extension

Tests live at `packages/csafe-codec/tests/`:

- `test_bindings.py` — framing-level binding tests
- `test_ble_decoders.py` — per-characteristic class-based tests with error cases
- `test_vectors_ble.py` — YAML-driven parametrized runner (16 vectors across 14
  characteristics)
- `vectors/ble_decoders.yaml` — the test vector definitions

BLE characteristics covered: 0x0031–0x003F (14 total: GeneralStatus,
AdditionalStatus1/2/3, StrokeData, AdditionalStrokeData, SplitIntervalData,
AdditionalSplitIntervalData, EndOfWorkoutSummary, EndOfWorkoutAdditionalSummary,
EndOfWorkoutAdditionalSummary2, HeartRateBeltInfo, ForceCurveData, AdditionalStatus3,
LoggedWorkout).

Multiplexed dispatch: `decode_multiplexed` (0x0080) — 7 IDs fully supported, 7 return
`MuxLayoutDiffers` (different packet layout at mux level due to 20-byte BLE limit).
