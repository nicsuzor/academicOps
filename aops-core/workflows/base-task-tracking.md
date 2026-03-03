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

5. **Record commits and PRs** in the task log:

```python
mcp__pkb__append(
    id="<task-id>",
    content="PR: https://github.com/.../pull/123",
    section="Log"
)
```

6. Mark task as complete when done

This creates bidirectional traceability: commits reference tasks (via `Task:` trailer in [[base-commit]]), and tasks reference commits/PRs (via log entries).

## When to Skip

- [[simple-question]] - no task needed
- [[direct-skill]] - skill handles its own tracking
