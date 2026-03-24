---
name: BLE test vectors branch state
description:
  Current state of feat/ble-test-vectors branch — what was completed, what's next
type: project
---

The `feat/ble-test-vectors` branch added two commits on top of main:

1. `62f328f` — YAML test vectors + parametrized runner for all 14 BLE decoders
2. `eb4bd94` — devcontainer fix (symlink Rust toolchain into /usr/local/bin)

The branch is NOT yet merged/PRed. The work completes beads task `workspace-dn9.3`
(Generate test vectors from YAML spec).

**Why:** The CSAFE Codec — Decoders & Publication epic (workspace-dn9) is 80% done (4/5
children closed). The remaining child is `workspace-dn9.5` (Publish to crates.io and
PyPI), which is blocked on `workspace-m05.4` (Expose command builders to Python via
PyO3).

**How to apply:** The branch is ready for PR creation. The orchestrator should create a
PR for this branch, then identify that the next actionable work is `workspace-m05.4`.
