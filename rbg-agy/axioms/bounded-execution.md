---
description: Every command carries a terminating bound visible in the command itself; reap what you start.
trigger: off
---

## Bounded Execution — no commands that may never terminate

Every shell command, subprocess, and background task you spawn has a bounded, observable terminating condition visible in the command itself. Never initiate an operation whose runtime has no defined upper bound.

- **Prohibited:** `--watch`, `--follow`/`-f`, `tail -f`, `while true`, dev servers spawned with `&` and never reaped, uncapped polling loops, any flag that blocks until an external event without a timeout.
- **Substitutes:** explicit timeouts, iteration caps, polling with a maximum wait stated in the command.
- **Reap what you start.** Where a long-running process is genuinely required, capture its PID and kill it before your turn ends. Harness auto-backgrounding is not reaping — a process the harness reports as backgrounded is still alive and still yours.

"I expect this to finish quickly" is not a bound. The stated bound must also fall within the authorised budget.
