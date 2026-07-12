---
id: base-task-tracking
category: base
---

# Base: Task Tracking

**Composable base pattern.** Most workflows include this.

## Pattern

1. **Search for duplicates**: Search for related tasks — if a match exists, attach to it instead of creating new.
   `mcp__pkb__task_search(query="<keywords>", limit=5)`

2. **Resolve parent** (mandatory before creating any new task): Follow the [[references/hierarchy-quality-rules]] Parent Resolution Protocol — current task context → active epics → project root → ask user.

3. **Create task** with the resolved parent.

4. Claim the task to lock it.
5. Undertake work ...

- [ WORK ]
- Update task body with findings during work

6. **Record commits and PRs** in the task log:

```python
mcp__pkb__append(
    id="<task-id>",
    content="PR: https://github.com/.../pull/123",
    section="Log"
)
```

7. Mark task as complete when done

This creates bidirectional traceability: commits reference tasks (via `Task:` trailer in [[base-commit]]), and tasks reference commits/PRs (via log entries).

## When to Skip

- [[simple-question]] - no task needed
- [[direct-skill]] - skill handles its own tracking
