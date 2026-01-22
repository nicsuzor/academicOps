---
name: pull
category: instruction
description: Pull a task from queue, claim it (mark active), and mark complete when done
allowed-tools: Task, Bash, Read, Grep, Skill, AskUserQuestion
permalink: commands/pull
---

# /pull - Pull, Claim, and Complete a Task

**Purpose**: Get a task from the ready queue, claim it (mark status active), and mark it complete when finished.

## Workflow

### Step 1: Get a Task

Call `mcp__plugin_aops-core_tasks__get_ready_tasks(project="aops")` to get available tasks.

Returns tasks that are:
- Leaves (no children)
- No unmet dependencies
- Status: active or inbox
- Sorted by priority

**If a specific task ID is provided** (`/pull <task-id>`):
- Call `mcp__plugin_aops-core_tasks__get_task(id="<task-id>")` to load it
- If the task has children (leaf=false), navigate to the first ready leaf subtask instead

**If no tasks are ready**:
- Check active/inbox tasks for any that can be worked on
- If none exist, report and halt

### Step 2: Claim the Task (Mark Active)

```
mcp__plugin_aops-core_tasks__update_task(id="<task-id>", status="active")
```

That's it. The task is now claimed.

### Step 3: Mark Complete When Done

```
mcp__plugin_aops-core_tasks__complete_task(id="<task-id>")
```

## Arguments

- `/pull` - Get highest priority ready task and claim it
- `/pull <task-id>` - Claim a specific task (or its first ready leaf if it has children)

## Implementation Note

How you execute the task, how you verify it, how you commit/push—those are agent responsibilities, not `/pull` responsibilities. This skill just manages the queue state: get, claim, complete.
