---
name: BLE test vectors branch state
description:
  STALE — superseded by current beads state; kept only for historical PR reference.
  Check `bd show c2m-dn9.5` for current status instead.
type: project
---

**STALE as of 2026-08-27.** The `feat/ble-test-vectors` branch this memory described was
merged via PR #17
(`9c39e36 feat: add YAML test vectors and parametrized BLE decoder runner (#17)`), and
the beads prefix has since been renamed from `workspace-*` to `c2m-*` (commit
`8268608`). The old IDs `workspace-dn9.3` / `workspace-m05.4` no longer exist as such.

Current equivalent: the CSAFE Codec — Decoders & Publication epic is `c2m-dn9`. Its
remaining open child is `c2m-dn9.5` (Publish csafe-codec v0.1.0 to crates.io and PyPI),
which was READY (unblocked) as of 2026-08-27 — run `bd show c2m-dn9.5` and
`bd show c2m-dn9` to verify current status before acting on this.

See also [[project_ble_gateway_architecture]] for the separate, unrelated BLE gateway
hardware-validation track (epic `c2m-ooz`).
