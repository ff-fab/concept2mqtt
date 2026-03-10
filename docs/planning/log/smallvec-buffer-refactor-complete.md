## Epic Complete: Zero-alloc SmallVec Buffer Refactor

Introduced SmallVec stack-allocated buffers and write-into-buffer pattern across
the entire csafe-codec crate, eliminating heap allocations for all typical CSAFE
frame operations (byte stuffing, frame building, frame parsing, and command
encoding).

**Phases Completed:** 4 of 4

1. SmallVec + _into primitives (stuff/unstuff)
2. Zero-alloc frame building (build_standard/extended_frame_into)
3. Zero-alloc frame parsing (Frame/ExtendedFrame use FrameBuf)
4. Command encode_into pattern (Command + 5 proprietary enums)

**All Files Created/Modified:**

- `packages/csafe-codec/Cargo.toml`
- `Cargo.lock`
- `packages/csafe-codec/src/framing/mod.rs`
- `packages/csafe-codec/src/framing/tests.rs`
- `packages/csafe-codec/src/lib.rs`
- `packages/csafe-codec/src/commands/mod.rs`
- `packages/csafe-codec/src/commands/public.rs`
- `packages/csafe-codec/src/commands/proprietary.rs`
- `packages/csafe-codec/src/commands/tests.rs`

**Key Functions/Classes Added:**

- `FrameBuf` / `StuffBuf` type aliases
- `stuff_into` / `unstuff_into` (write-into-buffer byte stuffing)
- `stuff_byte_into` (private single-byte stuffing helper)
- `build_standard_frame_into` / `build_extended_frame_into` (with rollback)
- `Command::encode_into` + 5 proprietary `encode_into` methods
- `encode_commands_into`
- `encode_wrapper_into` (length-placeholder backpatch pattern)

**Test Coverage:**

- Total tests written: 19 new tests
- Total tests passing: 187
- All tests passing: yes

**Recommendations for Next Steps:**

- Learning doc 09 (SmallVec patterns) can be written as a follow-up
- Consider adding one-line doc comments to `encode_into` methods for API symmetry
