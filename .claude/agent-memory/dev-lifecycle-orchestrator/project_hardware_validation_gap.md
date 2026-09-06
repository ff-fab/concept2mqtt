---
name: project-hardware-validation-gap
description:
  The dev container has no Pi, PM5, second BLE adapter or iPhone, so BLE acceptance
  criteria must be split into automated vs. user-executed hardware steps
metadata:
  type: project
---

concept2mqtt's real target is a Raspberry Pi talking to a physical Concept2 PM5 over
BLE, but the development container has none of that hardware: no Pi, no PM5, no second
BLE adapter (hci1), and no iPhone for traffic capture.

**Why:** Work happens in a container while the erg and Pi live at the user's home.
Anything touching real BLE — connection stability, the official Concept2 iPhone app,
traffic captures — can only be executed by the user in person.

**How to apply:** When planning any BLE feature, split acceptance criteria into (a)
automated, verifiable here via unit tests against in-memory doubles, and (b)
hardware-dependent, which the user must run. For (b), deliver a runnable PoC script plus
a written manual procedure rather than claiming completion. Existing precedents:
`docs/planning/legacy/examples/` for hardware scripts and
`docs/testing/pm5-ble-relay-hardware-validation.md` for procedures. Leave the beads
issue open and report which criteria are still pending. See
[[feedback-flag-hardware-steps]] and [[feedback-validation-runs-on-pi-only]].
