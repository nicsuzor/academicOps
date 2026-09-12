---
description: Record Dispatched claim on task before worker starts; two claims, not one.
trigger: off
---

## The Launch Claim

Record a dispatch claim on the task record (`Dispatched:` naming recipient, session, surface, and timestamp) before a worker starts, except for cheap read-only probes. The launcher records the dispatch; the worker claims to advance status, enabling sweeps to detect orphaned dispatches.
