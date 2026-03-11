## Epic PyO3 Command Builders Complete: Learning Document 09

Created `docs/learning/09-pyo3-command-classes-and-macros.md` — a comprehensive
pedagogical guide covering the PyO3 wrapper classes and declarative macro system
built in Phases 1–2. Covers 10 concepts including newtype wrappers, factory
methods, `macro_rules!`, raw identifiers, path aliasing, Vec conversion across
FFI, and the full Python-to-wire pipeline.

**Files created/changed:**
- `docs/learning/09-pyo3-command-classes-and-macros.md` (local-only, gitignored)

**Functions created/changed:**
- N/A (documentation only)

**Tests created/changed:**
- N/A (documentation only)

**Review Status:** APPROVED

**Git Commit Message:**
```
docs: add learning guide 09 — PyO3 command classes and macros

- Cover newtype wrapper pattern for exposing Rust enums to Python
- Explain declarative macros (macro_rules!) for FFI code generation
- Document raw identifiers, path aliasing, Vec conversion across FFI
- Trace full pipeline from Python factory methods to wire bytes
```
