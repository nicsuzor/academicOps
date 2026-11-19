---
trigger: always_on
description: Recurring jobs handle only what changed since the last completed run, stop when nothing changed, and never start concurrently.
---

## Recurring jobs: change-only and single-flight

Every recurring job handles only what changed since its last completed run (`since: <cursor>`), stops immediately when nothing changed, and never starts while another run of the same job is going.

- **Change-only execution:** A recurring job inspects its cursor at Step 0. If no underlying data, messages, events, or graph states have changed since the last completed run cursor, the job exits cleanly and immediately without dispatching subagents or rewriting documents.
- **Single-flight concurrency:** Every recurring job maintains an active in-progress lock marker. If an existing run is active and its heartbeat is fresh (< 15 minutes), any candidate run must halt immediately to prevent colliding executions or wasted token spend.
- **Durable cursors and atomic release:** Cursors tracking the last successful completion timestamp are stored in authoritative state records or document frontmatter. The cursor is updated and the lock cleared together when the run completes its handover.
