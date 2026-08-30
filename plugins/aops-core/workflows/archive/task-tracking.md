---
id: task-tracking
type: template
kind: fragment
category: fragment
description: Bookkeeping fragment — search for duplicates, resolve parent, claim, work, log, complete. Most process templates include this.
requires: []
pairs-with: []
conflicts: []
version: 1.0.0
permalink: workflows-process-task-tracking
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---
> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process fragment: Task Tracking

**Composable fragment.** Most process templates include this — it's how work
stays traceable on the graph, not a workflow in its own right.

## Pattern

1. **Search for duplicates** — if a matching task exists, attach to it instead
   of creating a new one.
2. **Resolve parent** (mandatory before creating any new task) — current task
   context → active epics → project root → ask user.
3. **Create task** with the resolved parent.
4. **Claim** the task to lock it.
5. **Undertake work** — check off items on the task checklist as they complete; capture durable findings into knowledge notes.
6. **Record output pointers** — link commits and PRs under `## Pointers` (no task logs).
7. **Mark complete** when done.

## When to Skip

- Pure information lookups (no task needed)
- A skill that handles its own tracking
