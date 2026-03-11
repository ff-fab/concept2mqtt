## Epic Command Builders Complete: PyO3 Bindings for Proprietary Commands

Exposed all 5 proprietary CSAFE command enums + public Command enum to Python via
macro-generated PyO3 wrapper classes with static factory methods. Added
`encode_commands()` and `build_command_frame()` top-level functions.

**Files created/changed:**

- `packages/csafe-codec/src/py_command_builders.rs` (created, 579 lines)
- `packages/csafe-codec/src/lib.rs` (modified — added module + registration)
- `packages/csafe-codec/python/csafe_codec/__init__.py` (modified — added imports)

**Functions created/changed:**

- `py_prop_command!` macro — generates `#[pyclass]` + `#[pymethods]` for each enum
- `PyGetPmCfgCommand` — 40 unit + 9 struct factory methods
- `PyGetPmDataCommand` — 48 unit + 11 struct factory methods
- `PySetPmCfgCommand` — 1 unit + 35 struct factory methods
- `PySetPmDataCommand` — 7 unit + 13 struct factory methods
- `PySetUserCfg1Command` — 6 struct factory methods
- `PyCommand` — 23 unit + 11 struct + 5 wrapper factory methods
- `py_encode_commands()` — encode command list to raw bytes
- `py_build_command_frame()` — encode + frame in one step

**Tests created/changed:**

- Existing 187 Rust tests — all pass
- Existing 142 Python tests — all pass

**Review Status:** APPROVED

**Git Commit Message:**

```text
feat: expose command builders to Python via PyO3 wrapper classes

- Add py_prop_command! macro for generating #[pyclass] wrappers
- Wrap all 5 proprietary command enums with static factory methods
- Add PyCommand class for public + wrapper commands
- Add encode_commands() and build_command_frame() Python functions
- Re-export all new classes from csafe_codec.__init__
```
