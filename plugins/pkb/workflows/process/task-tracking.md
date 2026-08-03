---
id: task-tracking
kind: process
category: fragment
description: Bookkeeping fragment — search for duplicates, resolve parent, claim, work, log, complete. Most process templates include this.
requires: []
pairs-with: []
conflicts: []
version: 1.0.0
permalink: workflows-process-task-tracking
---

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
5. **Undertake work** — update the task body with findings as you go.
6. **Record commits and PRs** in the task log — this creates bidirectional
   traceability: commits reference tasks (`Task:` trailer, see the
   [[wf-handover]] gate), tasks reference commits/PRs (log entries).
7. **Mark complete** when done.

## When to Skip

- Pure information lookups (no task needed)
- A skill that handles its own tracking
