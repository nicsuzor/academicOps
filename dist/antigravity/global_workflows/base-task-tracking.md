---
id: base-task-tracking
category: base
---

# Base: Task Tracking

**Composable base pattern.** Most workflows include this.

## Pattern

1. Search existing tasks for match
2. If no match: create task with clear title
3. Claim the task to lock it.
4. Undertake work ...
  - [ WORK ]
  - Update task body with findings during work
5. Mark task as complete when done

## When to Skip

- [[simple-question]] - no task needed
- [[direct-skill]] - skill handles its own tracking
