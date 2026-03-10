## Epic Command Types Phase 1 Complete: Value Enums + Public Command Enum

Foundation layer for CSAFE command types — 8 shared value enums generated via
a `csafe_enum!` macro, a flat `Command` enum covering all 39 PM5-supported
public commands (23 short + 16 long), and comprehensive tests.

**Files created/changed:**

- `packages/csafe-codec/src/commands/mod.rs`
- `packages/csafe-codec/src/commands/types.rs`
- `packages/csafe-codec/src/commands/public.rs`
- `packages/csafe-codec/src/commands/tests.rs`
- `packages/csafe-codec/src/lib.rs` (added `pub mod commands;`)

**Functions created/changed:**

- `csafe_enum!` macro — generates `#[repr(u8)]` enum + `TryFrom<u8>` + `Display`
- `Command::id()` — returns CSAFE command ID byte
- `Command::is_short()` — distinguishes short (0x80–0xFF) from long (0x00–0x7F)

**Tests created/changed:**

- 31 new tests: enum round-trips for all 8 value enums, invalid-value rejection,
  display output, all command ID mappings, `is_short()` polarity, wrapper IDs

**Review Status:** APPROVED

**Git Commit Message:**

```
feat: define CSAFE command types and value enums

- Add 8 shared value enums (WorkoutType, IntervalType, etc.) via csafe_enum! macro
- Add public Command enum with 23 short + 16 long PM5-supported variants
- Implement id() and is_short() methods on Command
- Add 31 tests covering enum round-trips and command ID mappings
```
