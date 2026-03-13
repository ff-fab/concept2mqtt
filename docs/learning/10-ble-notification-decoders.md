# 10 — BLE Notification Decoders: Fixed-Layout Binary Parsing and Enum Dispatch

> **Builds on:** [04 — Frame Parser](04-frame-parser-error-conversion-guide.md)
> (error enums, `Result`, length validation),
> [07 — Command Types](07-command-types-and-repr-enums.md)
> (enum design, `#[non_exhaustive]`),
> [08 — Command Encoding](08-command-encoding-and-match-ergonomics.md)
> (match arms, byte assembly).
>
> **New concepts:** `#[inline]` helper functions for byte assembly, the
> "struct-per-characteristic" pattern for fixed-layout binary protocols,
> enum-based multiplexed dispatch with `From` error conversion, and
> signed integer decoding (`i16::from_le_bytes`).

---

## What We Built

A **`ble` module** that decodes raw BLE notification payloads from the PM5's
Rowing Service into typed Rust structs — one struct per GATT characteristic:

```
BLE notification bytes                    Rust
─────────────────────                     ────
[0x01, 0x02, 0x03, ...]  (19 bytes)  →   GeneralStatus { elapsed_time_cs: 197121, ... }
[0x3B, 0x01, 0x02, ...]  (mux'd)    →   RowingCharacteristic::HeartRateBeltInfo(...)
```

| What was added                              | Where                  |
|---------------------------------------------|------------------------|
| 14 decoder structs + `decode_*` functions   | `ble/mod.rs`           |
| `RowingCharacteristic` enum + mux dispatch  | `ble/mod.rs`           |
| `BleDecodeError` / `MultiplexedError`       | `ble/mod.rs`           |
| 36 tests (round-trip, boundary, dispatch)   | `ble/tests.rs`         |

---

## Concept 1: Fixed-Layout Binary Parsing

### The Pattern

Every PM5 BLE characteristic has a fixed byte layout documented in
`ble_services.yaml`.  The bytes arrive as a flat `&[u8]` slice.  Our job
is to:

1. Validate the slice length.
2. Assemble multi-byte fields from individual bytes.
3. Return a typed struct.

```rust
pub fn decode_general_status(data: &[u8]) -> Result<GeneralStatus, BleDecodeError> {
    check_len(data, 19)?;               // Step 1: validate
    Ok(GeneralStatus {
        elapsed_time_cs: u24(data[0], data[1], data[2]),  // Step 2: assemble
        distance_dm: u24(data[3], data[4], data[5]),
        workout_type: data[6],           // single bytes: direct copy
        // ...
    })
}
```

### Why This Shape

Contrast this with how you'd do it in Python:

```python
# Python — struct.unpack with a format string
import struct
fields = struct.unpack('<HBHBBBBBBHBHBBB', data)  # opaque magic string
elapsed_time = fields[0]
```

The Rust approach is more verbose but has concrete advantages:

1. **No format string to get wrong.** Each field's offset and width is explicit
   in the code, not encoded in a dense `'<HBHBBBBBB...'` string where one
   misplaced letter shifts every subsequent field.

2. **Compile-time type safety.** The struct fields have named types — you can't
   accidentally treat a `u8` stroke rate as a `u16` distance.

3. **Zero-cost abstraction.** The helpers like `u24()` are `#[inline]` and
   compile down to the same shift-and-OR instructions you'd write by hand.

### Python Comparison: `struct.unpack` vs Manual Assembly

```python
# Python: these produce the same result
elapsed = struct.unpack_from('<I', b'\x01\x02\x03\x00', 0)[0] & 0xFFFFFF
elapsed = data[0] | (data[1] << 8) | (data[2] << 16)  # manual — same as Rust
```

In Rust there is no `struct.unpack`.  We write the manual version, but
the compiler optimises it identically to a single little-endian load on
platforms that support unaligned reads:

```rust
fn u24(lo: u8, mid: u8, hi: u8) -> u32 {
    u32::from(lo) | (u32::from(mid) << 8) | (u32::from(hi) << 16)
}
```

The `u32::from(lo)` is Rust's explicit widening cast — equivalent to
Python's implicit int promotion, but visible.

---

## Concept 2: `#[inline]` Helper Functions

```rust
#[inline]
fn u16le(lo: u8, hi: u8) -> u16 {
    u16::from(lo) | (u16::from(hi) << 8)
}
```

### What `#[inline]` Does

`#[inline]` is a *hint* to the compiler: "this function is small and hot;
please substitute its body at the call site rather than emitting a function
call."  It's the Rust equivalent of a C `inline` — not guaranteed, but
strongly encouraged.

For these 1-line helpers the compiler would almost certainly inline them
anyway, but the annotation makes the intent explicit and ensures
consistent behaviour across optimisation levels (debug builds respect
`#[inline]` more reliably than they auto-inline).

### Python comparison

Python has no equivalent.  Every function call in CPython goes through the
full call machinery.  This is why `struct.unpack` exists — it batches the
work into one C call rather than N Python function calls.  In Rust, inlined
helpers are *free* — the optimizer removes the call entirely.

---

## Concept 3: Signed Integer Decoding

Most fields are unsigned, but force curve data points are signed 16-bit:

```rust
fn i16le(lo: u8, hi: u8) -> i16 {
    i16::from_le_bytes([lo, hi])
}
```

`i16::from_le_bytes` is a standard library function that reinterprets two
bytes as a signed 16-bit integer in little-endian order.  This handles
two's complement automatically:

```rust
i16le(0xCE, 0xFF)  // → -50
//  0xFFCE in two's complement = -50
```

In Python you'd use `struct.unpack('<h', bytes([0xCE, 0xFF]))[0]`.

---

## Concept 4: The Struct-per-Characteristic Pattern

Each BLE characteristic maps to its own Rust struct:

```rust
pub struct GeneralStatus {
    pub elapsed_time_cs: u32,    // 24-bit assembled into u32
    pub distance_dm: u32,        // 24-bit assembled into u32
    pub workout_type: u8,
    // ... 8 more fields
}
```

### Design Decisions

**Why `u32` for 24-bit values?**  Rust has no `u24` type.  We use the next
larger type (`u32`) and document the actual width in comments.  The upper
byte is always 0.  This is idiomatic — the same choice the standard library
makes with `char` (a Unicode scalar value stored in `u32` even though only
21 bits are used).

**Why raw protocol units?**  Fields like `elapsed_time_cs` store centiseconds
as integers rather than converting to `f64` seconds.  This preserves exact
values and avoids floating-point surprises.  Conversion belongs in the
application layer (or the Python bindings), not the codec.

**Why `pub` on every field?**  These are pure data carriers — no invariants
to protect.  Making fields public avoids getters and lets consumers
destructure:

```rust
let GeneralStatus { elapsed_time_cs, distance_dm, .. } = decode_general_status(&bytes)?;
```

---

## Concept 5: Variable-Length Decoding (Force Curve)

Most characteristics are fixed-size.  Force curve data is the exception —
its header encodes the point count:

```rust
pub fn decode_force_curve_data(data: &[u8]) -> Result<ForceCurveData, BleDecodeError> {
    check_len(data, 2)?;                  // minimum: header + sequence

    let header = data[0];
    let point_count = header & 0x0F;      // LS nibble

    if point_count > 9 {                  // protocol max
        return Err(BleDecodeError::ForceCurveOverflow { ... });
    }

    let required = 2 + (point_count as usize) * 2;
    check_len(data, required)?;           // second validation with dynamic size

    let mut data_points = Vec::with_capacity(point_count as usize);
    for i in 0..point_count as usize {
        let offset = 2 + i * 2;
        data_points.push(i16le(data[offset], data[offset + 1]));
    }
    // ...
}
```

Key pattern: **two-phase validation**.  First check the minimum (header
exists), then decode the header to learn the actual size, then validate
again.  This avoids panics from out-of-bounds indexing while keeping error
messages precise.

### `Vec::with_capacity`

```rust
Vec::with_capacity(point_count as usize)
```

Pre-allocates exactly the right amount of memory.  Without this, `Vec`
would start small and reallocate as elements are pushed.  Since we know the
count upfront, one allocation suffices.

In Python, `list` always over-allocates.  In Rust, you choose your
allocation strategy explicitly.

---

## Concept 6: Enum-Based Multiplexed Dispatch

The PM5 multiplexed channel (0x0080) prefixes each payload with a
characteristic ID byte.  We dispatch with a match:

```rust
pub enum RowingCharacteristic {
    GeneralStatus(GeneralStatus),
    AdditionalStatus1(AdditionalStatus1),
    // ... 10 more variants
}

pub fn decode_multiplexed(data: &[u8]) -> Result<RowingCharacteristic, MultiplexedError> {
    let id = data[0];
    let payload = &data[1..];

    match id {
        0x31 => Ok(RowingCharacteristic::GeneralStatus(
            decode_general_status(payload)?
        )),
        0x32 => Ok(RowingCharacteristic::AdditionalStatus1(
            decode_additional_status_1(payload)?
        )),
        // ...
        _ => Err(MultiplexedError::UnknownId { id }),
    }
}
```

### The `From` Conversion for Error Types

The `?` operator in each match arm converts `BleDecodeError` into
`MultiplexedError`.  This works because we implement `From`:

```rust
impl From<BleDecodeError> for MultiplexedError {
    fn from(e: BleDecodeError) -> Self {
        Self::Decode(e)
    }
}
```

This is the same pattern from [doc 04](04-frame-parser-error-conversion-guide.md),
but now layered: `BleDecodeError` → `MultiplexedError`.  The `?` operator
calls `.into()` automatically, which finds this `From` impl.

### Python Comparison

```python
# Python equivalent — a dict dispatch table
DECODERS = {
    0x31: decode_general_status,
    0x32: decode_additional_status_1,
    # ...
}

def decode_multiplexed(data: bytes):
    decoder = DECODERS.get(data[0])
    if decoder is None:
        raise ValueError(f"unknown id: 0x{data[0]:02X}")
    return decoder(data[1:])
```

The Rust version is more verbose but gives you exhaustiveness checking —
if you add a new variant to `RowingCharacteristic`, the compiler forces you
to handle it everywhere the enum is matched.

---

## Concept 7: Error Type Composition

The module has two error types that serve different scopes:

```rust
// Low-level: any single-characteristic decode failure
pub enum BleDecodeError {
    InsufficientBytes { expected: usize, actual: usize },
    ForceCurveOverflow { claimed_points: u8, max_points: u8 },
}

// High-level: multiplexed channel failures (wraps BleDecodeError)
pub enum MultiplexedError {
    Empty,
    UnknownId { id: u8 },
    Decode(BleDecodeError),    // ← wraps the lower-level error
}
```

The `std::error::Error` impl on `MultiplexedError` uses `source()` to
chain errors:

```rust
impl std::error::Error for MultiplexedError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Decode(e) => Some(e),
            _ => None,
        }
    }
}
```

This is Rust's equivalent of Python's `raise ... from e` chaining.  When
you print the error with a library like `anyhow`, it shows the full chain:
`"decode error: BLE notification too short: expected 19 bytes, got 3"`.

---

## Testing Patterns

### The `assert_too_short` Helper

```rust
fn assert_too_short<T: std::fmt::Debug>(
    decoder: fn(&[u8]) -> Result<T, BleDecodeError>,
    expected_len: usize,
) {
    let short = vec![0u8; expected_len - 1];
    let err = decoder(&short).unwrap_err();
    assert_eq!(err, BleDecodeError::InsufficientBytes {
        expected: expected_len,
        actual: expected_len - 1,
    });
}
```

This uses a **function pointer** (`fn(&[u8]) -> Result<T, BleDecodeError>`)
to parameterise the test helper — one helper covers all 14 characteristics.
The `T: std::fmt::Debug` bound is needed so `unwrap_err()` can print the
`Ok` value if the assertion unexpectedly succeeds.

### Round-Trip Tests

Each characteristic has a round-trip test that constructs a byte array with
known values, decodes it, and asserts each field.  This is the
boundary-value analysis technique (ISTQB) — we test specific values at
interesting boundaries (zero, max single byte, multi-byte boundaries)
rather than random data.

---

## Key Takeaways

| Concept | Rust | Python |
|---------|------|--------|
| Byte assembly | `u32::from(lo) \| (u32::from(hi) << 8)` | `struct.unpack('<H', data)` |
| Inline hints | `#[inline]` — zero-cost at call site | Not possible (every call has overhead) |
| Signed decode | `i16::from_le_bytes([lo, hi])` | `struct.unpack('<h', data)` |
| Pre-allocation | `Vec::with_capacity(n)` | `list` auto-grows |
| Error chaining | `From` impl + `?` operator | `raise ... from e` |
| Exhaustive dispatch | `match` on enum (compiler-checked) | `dict.get()` dispatch table |
| Validation | Two-phase `check_len` for variable formats | `len(data) >= N` guards |
