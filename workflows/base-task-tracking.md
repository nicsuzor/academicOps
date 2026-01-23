---
id: base-task-tracking
category: base
---

# Base: Task Tracking

**Composable base pattern.** Most workflows include this.

## Pattern

1. Search existing tasks for match
2. If match: claim it (status=active)
3. If no match: create task with clear title
4. Update task body with findings during work
5. Complete task when done

## When to Skip

- [[simple-question]] - no task needed
- [[direct-skill]] - skill handles its own tracking
