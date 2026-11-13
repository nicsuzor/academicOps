---
name: dispatch-queue
description: Rank and present queued repo-scoped epic tasks ready for dispatch with recommendations, and launch polecat containers on tasks the user approves per wf-dispatch-queue. Use for "what's ready", "what should we dispatch", or "dispatch the queue". Exclude for non-interactive dispatch of named tasks (use /dispatch) or graph truth maintenance (use /reconcile).
---

# Dispatch Queue

Present queued repo-scoped epic tasks ready for dispatch, ranked with a recommendation on each, and launch polecat containers on tasks the user approves per universal workflow template `wf-dispatch-queue`.

Execute the pass by following universal workflow template `wf-dispatch-queue` (`../workflow-library/workflows/wf-dispatch-queue.md`).
