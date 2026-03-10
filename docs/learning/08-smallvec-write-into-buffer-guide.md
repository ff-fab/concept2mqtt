# 08 — SmallVec and the Write-Into-Buffer Pattern

> **Builds on:** [03 — Frame Builder](03-frame-builder-composition-guide.md)
> (`Vec::with_capacity`, frame construction),
> [04 — Frame Parser](04-frame-parser-error-conversion-guide.md) (error types,
> `Result`),
> [07 — Command Types](07-command-types-and-repr-enums.md) (command encoding,
> wrapper pattern).
>
> **New concepts:** `SmallVec` for stack-allocated buffers, the write-into-buffer
> (append) pattern, type aliases as domain vocabulary, the wrapper/delegation
> pattern for backward compatibility, the length-placeholder backpatch trick,
> and rollback-on-error with `truncate`.

---

## What We Built

A zero-heap-allocation path through the entire CSAFE codec pipeline — from
command encoding through frame building to wire output — for buffers that fit on
the stack.

```
Command::encode_into(buf)     ← push opcode + fields into FrameBuf
    │
    ▼
build_standard_frame_into(buf) ← inline stuffing, checksum, rollback on error
    │
    ▼
FrameBuf on the stack          ← 128 bytes, no malloc for typical frames
    │
    ▼
.into_vec()                    ← only at the FFI boundary (Python needs heap)
```

The old API (`encode()`, `build_standard_frame()`) still works — each function
is now a three-line wrapper around the `_into` variant.

---

## Concept 1: Why `SmallVec`?

### The Problem with `Vec<u8>`

Every `Vec::new()` or `vec![...]` in Rust goes to the heap allocator. For the
CSAFE codec, we're building small byte buffers (≤120 bytes for a standard frame)
thousands of times per second. Each allocation:

1. Calls `malloc` / `jemalloc` — even "fast" allocators have overhead
2. May cause cache misses — the buffer could land anywhere in memory
3. Eventually needs `free` at drop — another syscall's worth of bookkeeping

For buffers this small, the allocation overhead can exceed the cost of the actual
work.

### SmallVec: Stack First, Heap If Needed

[`smallvec`](https://docs.rs/smallvec) is a drop-in `Vec` replacement with an
inline buffer:

```rust
use smallvec::SmallVec;

// 128 bytes of inline storage — lives on the stack, not the heap
let mut buf: SmallVec<[u8; 128]> = SmallVec::new();
buf.push(0xF1);
buf.extend_from_slice(&[0x91, 0x92]);

// If we exceed 128 bytes, SmallVec silently spills to the heap.
// Same API as Vec — push, extend, index, iterate, etc.
```

**How it works internally:**

```
SmallVec<[u8; 128]>:
┌──────────────────────────────────────────────┐
│ discriminant (1 bit: inline or heap)         │
│ length: usize                                │
│ union {                                      │
│   inline: [u8; 128]    ← used when len ≤ 128│
│   heap: (*ptr, cap)    ← used when len > 128│
│ }                                            │
└──────────────────────────────────────────────┘
```

The struct itself sits on the stack (or wherever the caller placed it). No
allocator call happens until `len > N`.

### Choosing Buffer Sizes

The sizes aren't arbitrary — they come from the protocol:

| Type alias | Size | Reasoning |
|-----------|------|-----------|
| `FrameBuf = SmallVec<[u8; 128]>` | 128 B | CSAFE max frame = 120 bytes; 128 is the next power of two |
| `StuffBuf = SmallVec<[u8; 256]>` | 256 B | Worst case: every byte stuffed → 2× expansion of ~118 content bytes |

**Why powers of two?** SmallVec stores the buffer inline in the struct. Powers of
two align well with CPU cache lines (64 bytes) and avoid padding waste. They also
make it easy to reason about: "128 bytes? That's two cache lines."

**Why type aliases, not newtypes?** A type alias (`type FrameBuf = SmallVec<...>`)
gives us domain vocabulary without wrapping overhead. Code reads `FrameBuf`
instead of `SmallVec<[u8; 128]>`, but we keep full access to SmallVec's API.
A newtype wrapper would force us to re-export every method we need.

> **Ecosystem context:** `smallvec` is one of the most depended-upon crates in
> the Rust ecosystem — used by Servo, rustc itself, and dozens of foundational
> libraries. Version 1.x is stable and mature. The `bytes` crate was considered
> but rejected: it's designed for async networking (Arc-based sharing, 32-byte
> struct overhead) and would be overkill for small synchronous protocol buffers.

---

## Concept 2: The Write-Into-Buffer Pattern

### The Anti-Pattern: Allocate-and-Return

The original code created a new `Vec` per operation:

```rust
// ❌ Every call allocates a fresh Vec on the heap
pub fn stuff_bytes(data: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(data.len());
    for &b in data {
        if is_reserved(b) {
            out.push(ESCAPE);
            out.push(b - OFFSET);
        } else {
            out.push(b);
        }
    }
    out
}
```

When building a frame, we'd call `stuff_bytes` for the body, then again for the
checksum, then concatenate — three allocations where one would suffice.

### The Pattern: Append to Caller's Buffer

```rust
// ✅ Zero allocations — appends to whatever buffer the caller provides
pub fn stuff_into(data: &[u8], buf: &mut StuffBuf) {
    buf.reserve(data.len());
    for &b in data {
        if STUFF_RANGE.contains(&b) {
            buf.push(STUFF_MARKER);
            buf.push(b - EXTENDED_START);
        } else {
            buf.push(b);
        }
    }
}
```

**Key properties:**

1. **Appends, doesn't overwrite** — the function adds to whatever's already in
   `buf`. This lets callers compose operations: stuff the body, then stuff the
   checksum, all into the same buffer.

2. **Caller owns the buffer** — the caller decides the buffer type (`SmallVec`,
   `Vec`, anything with `push`/`extend`). Allocation policy is the caller's
   concern.

3. **`reserve` hint** — a single `reserve` call up front avoids repeated
   reallocation during the loop. We use `data.len()` as the minimum (unstuffed
   output is never smaller than input).

> **Design pattern:** This is the **Builder pattern** applied to byte buffers —
> the same idea as `std::fmt::Write` or `std::io::Write`. In Go it's
> `io.Writer`; in Java it's `OutputStream`. The core insight: **separate the
> "what to write" from the "where to write it"**.

### Naming Convention

Every `_into` function follows the same contract:

| Original | Into variant | Buffer type |
|----------|-------------|-------------|
| `stuff_bytes()` | `stuff_into()` | `&mut StuffBuf` |
| `unstuff_bytes()` | `unstuff_into()` | `&mut FrameBuf` |
| `build_standard_frame()` | `build_standard_frame_into()` | `&mut FrameBuf` |
| `build_extended_frame()` | `build_extended_frame_into()` | `&mut FrameBuf` |
| `Command::encode()` | `Command::encode_into()` | `&mut FrameBuf` |
| `encode_commands()` | `encode_commands_into()` | `&mut FrameBuf` |

The `_into` suffix is a Rust convention (see `Vec::clone_into`, `Read::read_to_string`,
`collect_into` nightly). It signals: "I write _into_ something you provide."

---

## Concept 3: The Wrapper/Delegation Pattern

### Backward Compatibility Without Code Duplication

We wanted zero-alloc `_into` functions without breaking the existing API. The
solution: make every old function a thin wrapper around the new one.

```rust
/// Build a standard CSAFE frame (original API — still works).
pub fn build_standard_frame(contents: &[u8]) -> Result<Vec<u8>, FrameError> {
    let mut buf = FrameBuf::new();
    build_standard_frame_into(contents, &mut buf)?;
    Ok(buf.into_vec())
}
```

Three lines, every time:

1. Create a fresh `FrameBuf` (stack-allocated — free)
2. Delegate to the `_into` variant (does all the work)
3. Convert to `Vec<u8>` via `.into_vec()` (one heap copy for the return value)

**Why `.into_vec()` and not just return the SmallVec?** The public API returns
`Vec<u8>`, which is the universally understood type. `SmallVec::into_vec()` is an
`O(n)` copy if the data is inline, or a zero-cost move if it already spilled to
the heap. Internal code can use `FrameBuf` directly and skip that final copy.

> **Principle: Open/Closed (SOLID).** The module is _open for extension_ (new
> `_into` functions for zero-alloc usage) but _closed for modification_ (the old
> `Vec`-returning API is unchanged). Callers that don't need zero-alloc
> performance keep working without changes.

---

## Concept 4: Rollback on Error with `truncate`

### The Problem

`build_standard_frame_into` appends to a caller-provided buffer. If the frame
turns out to be too large (after stuffing expands it), we've already polluted the
buffer with partial data. We need to leave the buffer unchanged on error.

### The Solution: Snapshot and Rollback

```rust
pub fn build_standard_frame_into(
    contents: &[u8],
    buf: &mut FrameBuf,
) -> Result<(), FrameError> {
    // ➊ Snapshot the buffer length before we start
    let start_len = buf.len();

    buf.push(STANDARD_START);

    // ... stuff contents, compute checksum, stuff checksum, push STOP ...

    let frame_len = buf.len() - start_len;
    if frame_len > MAX_FRAME_SIZE {
        // ➋ Rollback: truncate to pre-call state
        buf.truncate(start_len);
        return Err(FrameError::TooLarge { actual: frame_len });
    }

    Ok(())
}
```

**How it works:**

1. Before writing anything, record `buf.len()` as `start_len`
2. Do all the work (push bytes, stuff, etc.)
3. If validation fails, `buf.truncate(start_len)` restores the buffer to its
   exact pre-call state — all appended bytes are discarded

`SmallVec::truncate` is essentially `self.len = new_len` for `Copy` types like
`u8` — zero cost, no destructors to run.

> **Analogy:** This is the same idea as a **database transaction rollback**. The
> "transaction" is everything between saving `start_len` and either returning
> `Ok(())` (commit) or calling `truncate` (rollback). The buffer's invariant —
> "contains only complete, valid data" — is maintained even on error.

---

## Concept 5: The Length-Placeholder Backpatch

### The Problem

CSAFE wrapper commands encode as `[opcode, length, ...sub-commands...]`. The
`length` byte must contain the total size of all encoded sub-commands, but we
don't know that size until we've encoded them all.

The old approach: encode sub-commands into a temporary `Vec`, measure its length,
then prepend the header. Two allocations.

### The Trick: Write a Placeholder, Patch It Later

```rust
fn encode_wrapper_into<T>(
    opcode: u8,
    cmds: &[T],
    encode_fn: fn(&T, &mut FrameBuf),
    buf: &mut FrameBuf,
) {
    buf.push(opcode);
    let len_idx = buf.len();   // ➊ Remember where the length byte is
    buf.push(0);               // ➋ Placeholder — we'll fix it later
    let payload_start = buf.len();
    for cmd in cmds {
        encode_fn(cmd, buf);   // ➌ Sub-commands append directly
    }
    buf[len_idx] = (buf.len() - payload_start) as u8;  // ➍ Backpatch
}
```

**Step by step:**

1. Push the opcode byte
2. Push `0` as a placeholder for the length byte, remembering its index
3. Encode all sub-commands — they append directly to the same buffer
4. Calculate `buf.len() - payload_start` to get the actual payload length, then
   write it back into the placeholder position

Zero temporary allocations. The `fn(&T, &mut FrameBuf)` function pointer keeps
the function generic across all five wrapper types without needing a trait.

> **Where you'll see this pattern:** Binary protocol encoders, packet builders,
> TLV (Type-Length-Value) encoders, ASN.1/BER writers, and database page
> formatters. Any time you need to write a length prefix before you know the
> actual length.

---

## Concept 6: Monomorphization Trade-Off

### What Happens at Compile Time

`SmallVec<[u8; 128]>` and `SmallVec<[u8; 256]>` are different types. Every
function that takes `&mut SmallVec<[u8; N]>` gets its own machine code copy for
each `N`:

```rust
fn stuff_into(data: &[u8], buf: &mut StuffBuf) { ... }  // StuffBuf = [u8; 256]
fn stuff_byte_into(b: u8, buf: &mut FrameBuf) { ... }   // FrameBuf = [u8; 128]
```

Even though the logic is identical, the compiler generates separate code for each
buffer size. This is **monomorphization** — Rust's approach to generics.

**The trade-off:**

| Aspect | Pro | Con |
|--------|-----|-----|
| Speed | No vtable dispatch, inlining possible | — |
| Binary size | — | Code duplicated per type parameter |
| Compile time | — | More code to compile |

For a codec library with two buffer sizes, this is a non-issue. For a library
with dozens of buffer sizes, you'd consider a trait-based approach (`dyn Write`)
to avoid code bloat.

### Stack Budget

Each `FrameBuf` is ~128 bytes on the stack; each `StuffBuf` is ~256 bytes. Plus
SmallVec's own bookkeeping (~24 bytes per instance). The default thread stack is
usually 2–8 MB, so even a few nested calls are fine:

```
build_standard_frame_into:  ~128 bytes (FrameBuf on stack)
  └─ stuff_byte_into:       ~0 bytes (operates on borrowed buf)
```

If you were allocating `SmallVec<[u8; 65536]>`, you'd want to be more careful.
Rule of thumb: **keep inline SmallVec capacity under 1 KB**.

---

## Concept 7: PyO3 Boundary — Where Heap Is Unavoidable

### The Exception to Zero-Alloc

Python objects live on the heap, managed by Python's garbage collector (CPython
reference counting). There's no way to hand Python a stack-allocated buffer. At
the FFI boundary, we must convert:

```rust
#[pyfunction(name = "parse_standard_frame")]
fn py_parse_standard_frame(data: &[u8]) -> PyResult<Vec<u8>> {
    parse_standard_frame(data)
        .map(|buf| buf.into_vec())   // FrameBuf → Vec<u8> → Python bytes
        .map_err(...)
}
```

`SmallVec::into_vec()` does one of two things:

- **Inline data (common case):** Allocates a `Vec` on the heap and copies the
  inline bytes into it. Cost: one `malloc` + `memcpy`.
- **Already spilled:** Extracts the existing heap pointer — zero-cost move.

This is fine because:

1. We only pay the cost once, at the boundary
2. All internal operations (frame parsing, command encoding) stay zero-alloc
3. The FFI crossing itself has overhead (GIL, type checks) that dwarfs a single
   small `memcpy`

> **Principle: Separation of Concerns.** The pure Rust layer optimizes for
> zero allocation. The FFI adapter handles the impedance mismatch. Neither
> layer compromises for the other.

---

## Summary

| Concept | What | Why |
|---------|------|-----|
| `SmallVec` | Stack-first buffer with heap fallback | Avoids `malloc` for small, hot buffers |
| Write-into-buffer | `fn foo_into(data, &mut buf)` | Caller controls allocation; composable |
| Wrapper/delegation | `fn foo() { foo_into(); .into_vec() }` | Backward compat without duplication |
| Rollback | `truncate(start_len)` on error | Transactional buffer safety |
| Length backpatch | Write `0`, fill in later | No temporary buffer for TLV encoding |
| Monomorphization | One code copy per SmallVec size | Speed vs. binary size trade-off |
| FFI boundary | `.into_vec()` at the edge | Python needs heap; Rust internals stay zero-alloc |

---

## Gotcha: `SmallVec` and `serde`

If you ever need to serialize a `FrameBuf` with `serde`, SmallVec has a
`serde` feature flag that must be explicitly enabled:

```toml
smallvec = { version = "1", features = ["serde"] }
```

Without it, you'll get cryptic "trait `Serialize` not implemented" errors on
types that _look_ like they should be serializable. We don't need `serde` in the
codec today, but it's the #1 surprise people hit with SmallVec.
