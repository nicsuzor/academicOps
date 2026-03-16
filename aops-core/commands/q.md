---
name: q
type: command
category: instruction
description: Quick-queue a task for later without hydration overhead
triggers:
  - "queue task"
  - "save for later"
  - "add to backlog"
  - "new task:"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: mcp__pkb__create_task, mcp__pkb__task_search
permalink: commands/q
---

# /q - Quick Queue

**Purpose**: Capture a task title immediately with minimal overhead. Use `/planning` to decompose and structure it later.

## Workflow

1. **Check for duplicates**: `mcp__pkb__task_search(query="<keywords>", limit=3)` — if a close match exists, report it and ask whether to proceed
2. **Create task** with title only (no body):

```
mcp__pkb__create_task(
  task_title="<clear, actionable title>",
  type="task",
  project="<infer from context>",
  priority=2,
  assignee="polecat"
)
```

3. **Report and HALT**: "Queued: [task-id] — [title]. Run `/planning` to decompose."

## Arguments

- `/q <description>` — queue with that title
- `/q P0 <description>` — queue at priority 0
- `/q nic: <description>` — assign to nic instead of polecat
