---
trigger: always_on
description: Forbid shell polling; use background dispatch and native notifications.
---

## No shell polling

- Never write `while`, `until`, or `sleep` loops to poll tools, logs, events, or subagents.
- Dispatch async work in background and use native notifications.
