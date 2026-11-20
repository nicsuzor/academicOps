---
trigger: always_on
description: Recurring jobs run change-only from cursors with single-flight locks.
---

## Recurring jobs

- **Change-only:** Check `since: <cursor>` at Step 0; exit if idle.
- **Single-flight:** Hold a lock marker; halt on an active heartbeat.
- **Atomic release:** Update the cursor and clear the lock together on handover.
