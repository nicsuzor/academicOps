---
title: Handover Workflow
type: automation
category: instruction
permalink: handover-workflow
tags:
  - dump
  - handover
  - workflow
  - emergency-handover-workflow
---

<!-- NS: make this a 'base' workflow and require just about EVERY task to go through the session end process. MANDATORY. also add git commit and cleanup. -->
# Task end handover workflow

Graceful session handover when work must stop immediately.

## Step 1: Identify Current Task

```
mcp__plugin_aops-core_tasks__list_tasks(status="active", limit=5)
```

If no task is active, evaluate whether meaningful work was done (see Edge Cases).

## Step 2: Update Task with Progress

Add a progress checkpoint to the current task:

```
mcp__plugin_aops-core_tasks__update_task(
  id="<task-id>",
  body="DUMP checkpoint: <summary of progress made>\n\n- What was accomplished\n- What remains to be done\n- Any blockers or decisions needed"
)
```

## Step 3: File Follow-up Tasks

For each incomplete work item from the current TodoWrite list:

```
mcp__plugin_aops-core_tasks__create_task(
  title="<incomplete task>",
  type="task",
  project="aops",
  priority=2,
  body="Follow-up from /dump on <date>. Context: <what the next agent needs to know>",
  parent="<parent-task-id>"  # if applicable
)
```

## Step 4: Persist to Memory (Optional)

If discoveries or learnings should be preserved:

```
mcp__memory__store_memory(
  content="Session dump <date>: <key learnings>",
  tags=["dump", "handover"],
  metadata={"task_id": "<current-task>", "reason": "emergency handover"}
)
```

Skip if no significant learnings to persist.

## Step 5: Output Framework Reflection

Output the reflection in **exact AGENTS.md format**:

```markdown
## Framework Reflection

**Prompts**: [Original request in brief]
**Guidance received**: [Hydrator/custodiet advice, or "N/A"]
**Followed**: [Yes/No/Partial - explain]
**Outcome**: partial
**Accomplishments**: [What was accomplished before dump]
**Friction points**: [What caused the dump, or "user interrupt"]
**Root cause** (if not success): [Why work couldn't complete]
**Proposed changes**: [Framework improvements identified, or "none"]
**Next step**: [Exact context for next session to resume]
```

**Critical**: `Outcome` must be `partial` for dumps (work incomplete).

## Step 6: Halt

After outputting the reflection, **stop working**. Do not:
- Start new tasks
- Attempt to fix issues
- Continue with other work

Output this message:

```
---
DUMP COMPLETE. Work paused at checkpoint.

To resume: `/pull <task-id>` or claim the follow-up tasks created above.
---
```

## Edge Cases

### No task currently claimed BUT work was completed

CREATE a historical task to capture the session's work:

```
mcp__plugin_aops-core_tasks__create_task(
  title="[Session] <brief description of work done>",
  type="task",
  project="<relevant project or 'aops'>",
  status="done",
  priority=3,
  body="Historical task created at /dump.\n\n## Work Completed\n<what was accomplished>\n\n## Outcome\n<success/partial/failed>\n\n## Context\n<any follow-up notes>"
)
```

This ensures all sessions leave an audit trail in the task system. Note in reflection: "Created historical task for session work"

### No task currently claimed AND no meaningful work done

- Skip Step 2
- Still file follow-ups for any incomplete todos
- Note in reflection: "No task was active"

### Memory server unreachable

- Log warning: "Memory persistence skipped (server unreachable)"
- Continue with remaining steps

### Multiple tasks active

- Update all with dump checkpoint
- Note in reflection which tasks were active

### No incomplete work

- Skip follow-up task creation
- Reflection outcome can be `success` if work was actually complete

## Key Rules

1. **Always reflect** - Framework Reflection is mandatory even for dumps
2. **Always checkpoint** - Update task before halting
3. **Always file follow-ups** - Don't leave work orphaned
4. **Actually halt** - Don't continue working after dump completes
