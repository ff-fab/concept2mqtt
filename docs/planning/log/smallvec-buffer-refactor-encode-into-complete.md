## Epic SmallVec Buffer Refactor Complete: Command encode_into

Added `encode_into(&self, buf: &mut FrameBuf)` to `Command` and all 5 proprietary
enums, using the write-into-buffer pattern with a length-placeholder backpatch for
wrapper commands. Existing `encode()` methods and `encode_commands()` are now thin
wrappers.

**Files created/changed:**

- `packages/csafe-codec/src/commands/mod.rs`
- `packages/csafe-codec/src/commands/public.rs`
- `packages/csafe-codec/src/commands/proprietary.rs`
- `packages/csafe-codec/src/commands/tests.rs`

**Functions created/changed:**

- `encode_commands_into()` — new, iterates commands and calls `encode_into`
- `encode_commands()` — rewritten as thin wrapper
- `Command::encode_into()` — new, pushes bytes into caller-provided buffer
- `Command::encode()` — rewritten as thin wrapper
- `encode_wrapper_into()` — new, replaces `encode_wrapper` with length-placeholder
  backpatch
- `GetPmCfgCommand::encode_into()` — new
- `GetPmDataCommand::encode_into()` — new
- `SetPmCfgCommand::encode_into()` — new
- `SetPmDataCommand::encode_into()` — new
- `SetUserCfg1Command::encode_into()` — new
- All 5 proprietary `encode()` methods — rewritten as thin wrappers

**Tests created/changed:**

- `encode_into_short_command` — new
- `encode_into_long_command` — new
- `encode_into_wrapper_command` — new
- `encode_commands_into_multiple` — new
- `encode_into_proprietary_sub_command` — new

**Review Status:** APPROVED

**Git Commit Message:**

```text
refactor: command encode_into write-into-buffer pattern

- Add encode_into to Command and all 5 proprietary enums
- Add encode_commands_into for zero-alloc multi-command encoding
- Replace encode_wrapper with encode_wrapper_into length-backpatch
- Rewrite all encode() methods as thin wrappers
- Add 5 new _into tests
```
