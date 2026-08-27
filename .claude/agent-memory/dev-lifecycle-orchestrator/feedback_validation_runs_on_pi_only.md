---
name: feedback-validation-runs-on-pi-only
description:
  Manual hardware procedures must need only the Pi and the iPhone — no Mac, Xcode or
  extra gear — and subjective pass/fail UAT beats protocol-log-backed proof
metadata:
  type: feedback
---

Write hardware validation procedures against the equipment the user already has: the
Raspberry Pi and an iPhone. Do not introduce a step requiring a Mac, Xcode
(PacketLogger), or any other host or instrument. Prefer tools already on the Pi —
BlueZ's `btmon`, plus debug logging in our own code — and add the logging if it is
missing rather than reaching for external tooling.

Equally, do not demand protocol-level captured logs as proof of a behavioural criterion.
"User acceptance test without real logging is fine": a subjective pass/fail comparison
against a direct-connection baseline (does live data show, do the controls work, does it
feel the same) is acceptable sign-off.

**Why:** The user has no Mac, so a Mac-dependent step makes the whole procedure
unexecutable and blocks the issue indefinitely. Rigor that costs equipment the user
lacks is worse than a lighter check they can actually run.

**How to apply:** When drafting any manual procedure or acceptance criterion for BLE (or
any hardware) work, check every step against "can this be done with just the Pi and the
phone?" before proposing it. When the Pi is itself the peer under test — e.g. the relay
is the GATT server the app connects to — it can observe the traffic directly; no sniffer
is needed. Applied on 2026-08-27 to `docs/testing/pm5-ble-relay-hardware-validation.md`.
See [[project-hardware-validation-gap]].
