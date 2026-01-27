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

## Quick Exit: No Work Done

If the session only involved answering user questions with no code changes, task work, or meaningful framework work:

```markdown
## Framework Reflection
Answered user's question: "<brief summary of question/topic>"
```

Then **stop** - skip all other steps.

---

## Step 1: Update Task with Progress

If you DID NOT claim a task AND you did meaningful work:
- You shouldn't have, but fix that now by creating a task to document your work.

Update your claimed task with progress and release it.

<!--@NS: add proper syntax here for updating and releasing the task. -->
```
mcp__plugin_aops-core_tasks__update_task(
  id="<task-id>",
)
```

## Step 2: Commit Changes (MANDATORY)

**Per P#24 (Trust Version Control)**: Commit AND push after completing logical work units.

If you made ANY changes (code, config, docs), commit them NOW before memory/reflection:

```bash
git status  # Review changes
git add <specific-files>  # Stage relevant changes
git commit -m "<type>: <description>"
git push  # Push to remote
```

**No uncommitted work is allowed at session end.** The commit message should summarize what was accomplished. Skip only if `git status` shows no changes.

### Polecat Worktree: Signal Ready for Merge

If you're working in a **polecat worktree** (path under `~/polecats/`), the work isn't complete until the Refinery merges it. Instead of marking the task `done`, signal it's ready for merge:

1. **Push the feature branch**:
```bash
git push -u origin polecat/<task-id>
```

2. **Set task status to `review`** (ready for merge):
```
mcp__plugin_aops-tools_task_manager__update_task(
  id="<task-id>",
  status="review"
)
```

3. **Do NOT mark as `done`** - the Refinery sets `done` after merging to main.

The task lifecycle in polecat workflow:
```
active → in_progress → review → done
         (claimed)    (you)    (refinery)
```

**CLI alternative**: If running interactively, use `polecat finish` which does steps 1-2 atomically.

## Step 3: File Follow-up Tasks

For each incomplete work item from the current session:

```
mcp__plugin_aops-core_tasks__create_task(
  title="<incomplete task>",
  type="task",
  project="aops",
  priority=2,
  body="Follow-up from <session id> on <date>. Context: <what the next agent needs to know>",
  parent="<parent-task-id>"  # if applicable
)
```

## Step 4: Persist to Memory

For each task complete and learning to persist:

```
mcp__memory__store_memory(
  content="<work done and key learnings>",
  tags=["dump", "handover"],
  metadata={"task_id": "<current-task>", "reason": "<reason (interrupted|complete|other|...)>"}
)
```


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
Work COMPLETE: [One line summary]

Next: `/pull <task-id>` to resume.
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


### Blocked by infrastructure bug (P#9/P#25)

When session ends because tooling failed and a bug was filed:

1. **Mark original task as blocked**:
```
mcp__plugin_aops-core_tasks__update_task(
  id="<original-task-id>",
  status="blocked",
  depends_on=["<bug-task-id>"]
)
```

2. **Reflection outcome**: `partial` with friction point explaining the infrastructure failure

3. **Do NOT leave task as "active"** - blocked tasks should be visible as blocked, not appear claimed

This ensures:
- Task tree shows blocking relationship
- Future sessions don't re-claim blocked work
- Bug must be fixed before original task can resume

## Key Rules

1. **Always reflect** - Framework Reflection is mandatory even for dumps
2. **Always checkpoint** - Update task before halting
3. **Always file follow-ups** - Don't leave work orphaned
4. **Actually halt** - Don't continue working after dump completes
