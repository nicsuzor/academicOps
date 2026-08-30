---
id: burst
type: template
kind: fragment
category: fragment
description: Stateful, multi-session batch lifecycle — init, run, persist, resume — for iterative work too large for one session
requires: [task-tracking]
pairs-with: []
conflicts: [batch]
version: 1.0.0
permalink: workflows-process-burst
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---

> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process fragment: Burst

A stateful alternative to [[batch]] for long-running, iterative batch
operations that span multiple agent sessions.

## When to Use

- Batch tasks taking more than one session (e.g. auditing 100+ files).
- Items needing evaluation before the next is dispatched.
- Work that must persist progress and resume exactly where it left off.

## Pattern

1. **Init**: define config (queue source, worker instructions, evaluation
   criteria); populate the queue by scanning the source; create a tracking
   task with the initial queue and state.
2. **Run** (the burst loop):
   - **Load** state from the tracking task.
   - **Evaluate** previous dispatches against criteria; mark items `done` or
     `failed`; return items needing another attempt to `pending`.
   - **Dispatch** pending items up to `items_per_burst`; create worker tasks.
3. **Persist**: update frontmatter counters, append an activity log to the
   task body, halt and report progress.
4. **Resume**: re-enter at step 2 using the tracking task ID.

## Skills Required

A `burst-supervisor` skill implements the loop's engine logic — this fragment
is the lifecycle shape, not the implementation.

## When to Skip

Use [[batch]] instead when the work fits in one session and items are
independent with no need for cross-session evaluation state.
