---
id: handover
title: Handover Workflow
type: automation
category: instruction
bases: [base-commit]
permalink: handover-workflow
tags:
  - dump
  - handover
  - workflow
  - emergency-handover-workflow
---

<!-- NS: make this a 'base' workflow and require just about EVERY task to go through the session end process. MANDATORY. also add git commit and cleanup. -->
<!-- @claude 2026-02-07: Agreed. This should become base-handover and be composed into all file-modifying workflows. Current MANDATORY section already covers git commit/push. Task created: aops-54ff7ab0. Will: (1) rename to base-handover.md, (2) add to bases: array in all relevant workflows, (3) ensure hydrator always includes handover steps. -->

# Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds and you output a framework reflection in the required form.

## MANDATORY WORKFLOW

1. **Complete all file changes** - Finish any pending edits, writes, or code modifications
2. **Run quality gates** - If code was changed, run tests and verify they pass
3. **Update task status** - Mark tasks complete or update progress as appropriate
4. **Invoke `/handover`** - Use the Skill tool with `skill="aops-core:handover"`
5. **Commit and PUSH** - The handover skill will guide you, but ensure `git push` succeeds
6. **Verify** - All changes committed AND pushed to remote
7. **Output Framework Reflection** - Provide context for the next session

## CRITICAL RULES

- Work is **NOT complete** until `git push` succeeds
- **NEVER stop** before pushing to remote
- If push fails, resolve and retry until it succeeds
- Using mutating tools (Edit, Write, Bash, git) after handover will reset the gate

## Quick Exit: No Work Done

If the session only involved answering user questions with no code changes, task work, or meaningful framework work:

```markdown
## Framework Reflection

User asked: "<brief summary of question/topic>"
Answer: "<summary of answer>"
Next steps: "<what the user or agent should do next, including task ID if applicable>"
```

Then **stop** - skip all other steps.

---

## Step 1: Update Task with Progress

If you DID NOT claim a task AND you did meaningful work:

- You shouldn't have, but fix that now by creating a task to document your work.

Update your claimed task with progress and release it.

<!--@NS: add proper syntax here for updating and releasing the task. -->
<!-- @claude 2026-02-07: Done. Updated with complete syntax including body append and status change. -->

```
mcp__plugin_aops-core_task_manager__update_task(
  id="<task-id>",
  body="## Session Progress\n- [What was accomplished]\n- [Any blockers or notes]",
  status="done"  # or "review" if needs human verification
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

If you're working in a **polecat worktree**, the work isn't complete until the Refinery merges it. Instead of marking the task `done`, signal it's ready for merge:

1. **Push the feature branch**:

```bash
git push -u origin polecat/<task-id>
```

2. **Set task status to `merge_ready`**:

```
mcp__plugin_aops-tools_task_manager__update_task(
  id="<task-id>",
  status="merge_ready"
)
```

3. **Do NOT mark as `done`** - the Refinery sets `done` after merging to main.

The task lifecycle in polecat workflow:

```
active → in_progress → merge_ready → done
         (claimed)    (you)     (refinery)
```

## Step 3: File Follow-up Tasks

For each incomplete work item from the current session:

```
mcp__plugin_aops-core_task_manager__create_task(
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
**Next step**: [Exact context for next session to resume, including Task ID]
```

**Critical**: `Outcome` must be `partial` for emergency handover (work incomplete).

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
mcp__plugin_aops-core_task_manager__create_task(
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
mcp__plugin_aops-core_task_manager__update_task(
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
