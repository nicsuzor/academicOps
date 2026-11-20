---
name: dispatch-queue
description: Rank and present queued repo-scoped tasks ready for dispatch with recommendations, and launch isolated worker containers on tasks the user approves. Use for "what's ready", "what should we dispatch", or "dispatch the queue". Exclude for non-interactive dispatch of named tasks (use /dispatch) or graph truth maintenance (use /reconcile).
---

# /dispatch-queue -- Interactive Queue Selection and Dispatch

Present queued repo-scoped tasks ready for dispatch in graph order, pair each with a dispatch recommendation (`dispatch`, `hold`, or `ask`) and concise rationale, and launch isolated worker containers via `/dispatch` only on tasks the user approves.

## Procedure

Resolve and execute the universal queue-selection and dispatch workflow template from `/workflow-library` (enumerating universal templates via native file tools):

1. **Candidate ranking**: Have the custodian query ready `queued` and promotable `ready` tasks from the graph in flow order without running pre-dispatch `/reify` or altering rank order.
2. **Present and confirm**: Present each candidate with its recommendation and one-clause reason for user approval (deferring unanswered lists to the daily note rather than auto-dispatching).
3. **Dispatch approved tasks**: Promote approved `ready` tasks to `queued`, invoke `/dispatch`, and record launch confirmations and hold reasons on the respective task records.
