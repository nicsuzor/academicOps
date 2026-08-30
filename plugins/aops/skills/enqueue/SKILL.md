---
name: enqueue
description: Mark a task ready for dispatch or re-dispatch
---

# /enqueue: user authority to enqueue a decomposed task

The user has explicitly asked to mark one or more tasks as ready for dispatch.

You should identify the task(s) to be enqueued and call the PKB's `update_task`
tool to update their status to 'queued'.

You should only enqueue tasks that are ripe:

- Most common is enqueing 'ready' (already decomposed) tasks.
- DO NOT queue 'inbox' tasks (not decomposed yet, not ready for dispatch)
- DO NOT queue any task whose body carries an unaddressed artifact rot annotation,
  premise falsification note, or KILL/NIC triage verdict — these belong in `inbox`
  or `cancelled` until explicitly re-briefed.
- You may mark a task for 're-dispatch' if it has already progressed beyond the queue ('in_progress', 'under_review', 'merge_ready', 'failed', etc.)
- Make sure the user's intent is totally clear before re-queueing a task that is marked 'done', 'cancelled' or 'archived' or similar terminal status. This usually signals either user error or a mismatch of PKB state.

Enqueuing a parent task will also enqueue all of its ready children.

## OUTPUT TEMPLATE

```
- **ENQUEUED Task [ task-id ] [task title] [ with n children ]
...
```
