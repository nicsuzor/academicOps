---
description: Every command carries a terminating bound visible in the command itself; reap what you start.
trigger: always_on
---

## Bounded Execution

Every command, subprocess, and background task must have a visible terminating condition. Prohibit `--watch`, `tail -f`, `while true`, and uncapped polling loops. Use explicit timeouts or iteration limits, and terminate spawned background processes before ending your turn.
