---
name: dispatch-queue
description: Show the user the tasks ready to dispatch, ranked with a recommendation on each, and start workers on the ones the user approves -- redirects to universal workflow template wf-dispatch-queue. Use for "what's ready", "what should we dispatch", or "dispatch the queue". Exclude for starting workers on named tasks without the user's choice (use dispatch) or graph truth maintenance (use reconcile).
---

# Dispatch queue

The canonical procedure is defined in universal workflow template `wf-dispatch-queue`.

Run the pass by resolving and executing `wf-dispatch-queue` via `/pull wf-dispatch-queue` or through the workflow library (`plugins/ida/skills/workflow-library/workflows/wf-dispatch-queue.md`).
