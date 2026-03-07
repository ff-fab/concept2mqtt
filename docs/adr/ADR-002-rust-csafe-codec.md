# ADR-002: Rust CSAFE Codec in Mono-repo

## Status

Accepted **Date:** 2026-03-07

## Context

concept2mqtt needs a CSAFE codec — the byte-level protocol for communicating with
Concept2 PM5 rowing monitors. The codec is pure, deterministic, byte-in/byte-out logic
with no I/O or async. This makes it an ideal candidate for a language that catches
byte-level errors at compile time rather than at runtime.

The project owner explicitly chose "Rust from day one" for the learning opportunity.
The codec's bounded scope (byte slices, enums, pattern matching — no lifetimes, no
async, no unsafe) makes it well-suited as a first Rust project.

Full deliberation is documented in the design sparring rounds
(`docs/planning/sparring-concept2mqtt-r2.md`, branch `docs/detailed-planning`).

## Decision

Implement the CSAFE codec in Rust, hosted in the same mono-repo at
`packages/csafe-codec/`, exposed to Python via PyO3 + maturin.

### Key choices

1. **Rust over pure Python** — for compile-time correctness guarantees, reusability
   (crates.io + C FFI), sub-millisecond `cargo test` runs, and learning value.
   Performance was _not_ the primary driver (~10 frames/sec is fine in Python).

2. **Mono-repo structure** — Cargo workspace at repo root, crate under
   `packages/csafe-codec/`. uv workspace integration means `uv sync` builds the
   native extension via maturin (PEP 517). This is the same pattern used by
   pydantic-core, polars, ruff, cryptography, and tokenizers.

3. **PyO3 0.24 + maturin** — community-standard binding mechanism. Python source in
   `packages/csafe-codec/python/csafe_codec/` re-exports from the `_native` module.
   Cross-compilation for aarch64 (Raspberry Pi) via `maturin-action` in CI.

4. **Independent release cycle** — csafe-codec publishes to both crates.io and PyPI
   with its own version, independent from concept2mqtt. MIT licensed.

## Decision Drivers

- Compile-time correctness for byte-level protocol logic
- Reusability across languages and ecosystems (crates.io, PyPI, C FFI)
- Learning value — Rust as a new language/paradigm for the project owner
- Developer experience — sub-second test cycles, seamless local builds via uv

## Considered Options

1. **Pure Python codec** — simpler toolchain, no compilation step. Rejected: runtime
   byte-level errors, Python-only consumers, no ecosystem play, no learning value.

2. **Separate repository** — cleaner separation. Rejected: cross-repo coordination
   overhead, no uv workspace for local dev, harder to keep in sync during iteration.

3. **cffi / ctypes** — no framework dependency. Rejected: manual memory management, no
   automatic type conversion, PyO3 is the community standard.

4. **Introduce Rust later** — lower initial risk. Rejected: codec scope is
   well-bounded and ideal for learning; deferring means rewriting working Python code.

## Consequences

### Positive

- Byte-level protocol errors caught at compile time, not at runtime
- Codec is reusable as a standalone Rust crate or Python package
- Fast feedback loop: `cargo test` in sub-second, `maturin develop --uv` for Python
- Proven mono-repo pattern with mature tooling (maturin, uv workspace, PyO3)

### Negative

- Rust toolchain required in dev environment and CI (handled by devcontainer)
- Cross-compilation adds CI complexity (maturin-action mitigates this)
- Contributors need basic Rust familiarity (mitigated by simple Rust subset used)

_2026-03-07_
