---
trigger: always_on
description: Bounded Execution — no commands that may never terminate
---

## Bounded Execution — no commands that may never terminate {#bounded-execution}

Every shell command, subprocess, or background task you spawn MUST have a bounded, observable terminating condition visible in the command itself. You MUST NOT initiate operations whose runtime has no defined upper bound.

- **Prohibited shapes:** `--watch`, `--follow`/`-f`, `tail -f`, run-watchers, `while true; do …; done`, dev servers spawned with `&` and never reaped, uncapped polling loops, any flag that "blocks until X" without a timeout.
- **Bounded substitutes:** explicit timeouts, iteration caps, polling with a maximum wait expressed in the command itself.
- **Reap what you start.** If a long-running process is genuinely required, capture its PID and kill it before your turn ends. Harness auto-backgrounding is not reaping — when the harness reports "running in background," that process is still alive and you own its termination.
- _E.g._ "I expect this to finish quickly" is not a bound; the upper bound must be stated in the command and fall within the authorised budget (`costly-ops-approval`).

_Review: [[AXIOMS-REVIEW#bounded-execution]]._
