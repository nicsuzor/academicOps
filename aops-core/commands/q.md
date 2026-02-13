---
name: q
category: instruction
description: Quick-queue a task for later without hydration overhead
allowed-tools: mcp__plugin_aops-tools_task_manager__create_task, mcp__plugin_aops-tools_task_manager__search_tasks, mcp__plugin_aops-tools_task_manager__update_task
permalink: commands/q
triggers: ["queue task", "save for later", "add to backlog", "new task:"]
---

# /q - Quick Queue

**Purpose**: Capture a task for later execution with minimal overhead.

## When to Use

- User says "new task: X" or "/q X"
- Quick capture of work that should NOT be executed now
- Backlog management without execution planning
- **Commission functionality**: Create task for swarm to implement instead of coding manually

## Workflow

### Step 1: Check for Duplicates (Quick Search)

Search for potentially related tasks:

```
mcp__plugin_aops-tools_task_manager__search_tasks(query="<keywords>", limit=5)
```

If a related task exists with status != "done":

- Ask user: "Found related task [ID]: [title]. Add as subtask, or create new?"
- If add: use `update_task` to append to body or decompose
- If new: proceed to Step 2

### Step 2: Route and Create Task

**Determine assignee**:

- `polecat`: Mechanical work, code changes, documentation (swarm-claimable)
- `nic`: Requires human judgment, external communication, decisions

**Determine priority**:

- P0: Blocking current work, critical bug
- P1: Workflow improvement, high-value feature
- P2: Normal backlog (default)
- P3: Nice-to-have, someday

**Create with context for workers**:

```
mcp__plugin_aops-tools_task_manager__create_task(
  task_title="<clear, actionable title>",
  type="task",  # or: bug, feature, learn
  project="<infer from context>",
  priority=2,
  assignee="polecat",  # or "nic" for human tasks
  tags=["<relevant>", "<tags>"],
  body="""# <Title>

## Problem
<What's wrong or missing>

## Solution
<What needs to happen>

## Files to Update
- `path/to/file.py` (if known)

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
"""
)
```

### Step 3: Confirm and HALT

Report: "Queued: [task-id] - [title] (assignee: polecat, P2)"

The task is queued. Swarm will claim if assignee=polecat.

## Task Body Template

Good task bodies help workers succeed:

```markdown
# <Title>

## Problem

<1-2 sentences on what's wrong>

## Solution

<How to fix it>

## Files to Update

- `path/to/relevant/file.py`

## Acceptance Criteria

- [ ] Testable criterion
```

## Arguments

- `/q <description>` - Create task with description as title
- `/q` (no args) - Prompt user for task details
- `/q P0 <description>` - Create high-priority task
- `/q bot <description>` - Explicitly assign to swarm

## Meta-Workflow: Commission Don't Code

When you encounter missing functionality:

1. **Don't debug manually** - create a task
2. Assign to `polecat` with clear acceptance criteria
3. Let swarm implement, file PR
4. Merge PR and use new feature

This keeps supervisor sessions lean and lets workers do implementation.
