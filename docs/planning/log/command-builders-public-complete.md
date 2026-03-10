## Epic CSAFE Codec — Command Builders Complete: Public Command Builders

Added `encode(&self) -> Vec<u8>` methods to all CSAFE command types, serialising
enum variants into raw wire bytes (before byte-stuffing/framing). Also added
`encode_commands()` to pack multiple commands into frame contents, plus a
learning document teaching match ergonomics, byte buffers, and recursive encoding.

**Files created/changed:**
- packages/csafe-codec/src/commands/public.rs
- packages/csafe-codec/src/commands/proprietary.rs
- packages/csafe-codec/src/commands/mod.rs
- packages/csafe-codec/src/commands/tests.rs
- docs/learning/08-command-encoding-and-match-ergonomics.md

**Functions created/changed:**
- `Command::encode(&self) -> Vec<u8>` — public command encoding
- `GetPmCfgCommand::encode(&self) -> Vec<u8>` — proprietary get-config encoding
- `GetPmDataCommand::encode(&self) -> Vec<u8>` — proprietary get-data encoding
- `SetPmCfgCommand::encode(&self) -> Vec<u8>` — proprietary set-config encoding
- `SetPmDataCommand::encode(&self) -> Vec<u8>` — proprietary set-data encoding
- `SetUserCfg1Command::encode(&self) -> Vec<u8>` — user-config encoding
- `encode_wrapper<T>()` — generic helper for wrapper command encoding
- `encode_commands(&[Command]) -> Vec<u8>` — multi-command frame contents

**Tests created/changed:**
- 35 new encoding tests covering all short/long commands, wrappers, empty wrappers,
  multi-command encoding, LE byte order, and representative proprietary sub-commands
- Total: 168 tests passing (133 existing + 35 new)

**Review Status:** APPROVED

**Git Commit Message:**
```
feat: implement CSAFE command encoding (public + proprietary)

- Add encode() to Command and all 5 proprietary sub-command enums
- Add encode_commands() for multi-command frame packing
- Add encode_wrapper<T>() generic helper for DRY wrapper encoding
- Add 35 encoding tests covering all command types
- Add learning doc 08: match ergonomics and byte buffers
```
