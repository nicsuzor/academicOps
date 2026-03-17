---
id: base-commit
category: base
---

# Base: Commit

**Composable base pattern.** Used when work modifies files.

## Pattern

After EVERY chunk of work:

1. Stage specific files (not `git add -A`)
2. Commit with clear message (why, not what)
3. **Include task ID** in the commit message body (see format below)
4. Push to remote

### Commit message format

```
<type>: <description>

<optional body explaining why>

Task: <task-id>
Epic: <epic-id>  # if applicable
```

The `Task:` trailer links the commit to the task graph. This enables tracing from git history back to the task that motivated the work. Include `Epic:` when the task is part of a larger initiative.

## When to Skip

- No file modifications made
- User explicitly requests no commit
