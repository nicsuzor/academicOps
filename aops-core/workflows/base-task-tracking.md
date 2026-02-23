---
id: base-task-tracking
category: base
---

# Base: Task Tracking

**Composable base pattern.** Most workflows include this.

## Pattern

1. Search existing tasks for match
2. If no match: create task with clear title
3. **Assess scope**: Is this actionable as a single task?
   - Path is uncertain, deliverable is vague, or work spans multiple sessions → invoke `/planning` skill to decompose before proceeding
   - Clear deliverable, known steps, single session → proceed
4. Claim the task to lock it
5. Undertake work ...

- [ WORK ]
- Update task body with findings during work

6. Mark task as complete when done

## When to Skip

- [[simple-question]] - no task needed
- Explicit skill invocation - skill handles its own tracking
