---
name: feedback-flag-hardware-steps
description:
  Never mark hardware-dependent acceptance criteria as done; flag them explicitly and
  leave the beads issue open for the user to close
metadata:
  type: feedback
---

Do not claim an acceptance criterion is met when it needs physical hardware. Flag it as
open, name exactly what the user must do, and leave the beads issue open — the user
closes it after validating in person.

**Why:** The user works from a container with no access to the Pi, PM5 or iPhone (see
[[project-hardware-validation-gap]]). A prematurely closed issue hides an unverified
assumption behind a green checkmark, and for BLE work the riskiest assumptions — which
GATT service the app actually speaks, whether the connection survives a long session —
are precisely the hardware-dependent ones.

**How to apply:** In the final report, list hardware-dependent criteria separately from
completed ones and state what artifact the user needs (script, procedure, capture file).
Use `bd note` to record the same split on the issue so the context survives the
conversation. Never `bd close` such an issue yourself.
