---
trigger: always_on
---

- **No Shell Polling:** NEVER write `while`, `until`, or `sleep` loops in Bash to call tools, poll log files, wait for events, or monitor subagents.
- **Checking Status:** Dispatch in the background instead, and use your harness's native functionality to get notified when it completes.
