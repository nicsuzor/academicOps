---
name: cowork-sync
type: skill
category: instruction
description: Mirror PKB tasks onto the Cowork native task list at claim time and sync completion back to PKB. Cowork-only; ships only in the cowork build of aops-core.
triggers:
  - "mirror task"
  - "sync task list"
  - "cowork task"
  - "native task list"
  - "TaskCreate"
  - "merge tasks onto cowork"
modifies_files: false
needs_task: false
mode: procedure
domain:
  - operations
platforms:
  - cowork
permalink: skills/cowork-sync
---

# /cowork-sync: PKB ↔ Native Task List Mirror

Defines procedures for aligning the Personal Knowledge Base (PKB) with the Cowork harness-native task list.

## Invariants

- PKB remains the system of record.
- Mirror claimed tasks from PKB onto the native list at `/pull` claim time.
- Write native task updates (`in_progress`, `completed`) to the native list.
- Sync native child completions back to PKB via `mcp__pkb__complete_task` in real time. Parent task sync is deferred to `/end_session`'s `release_task`.
- Every native task must store its PKB task ID in its `description` (e.g. `"PKB task-acba1234 — Implement X"`).

## Bootstrap

Before calling native task tools, ensure schemas are loaded:

```json
ToolSearch(query="select:TaskCreate,TaskUpdate,TaskList,TaskGet", max_results=4)
```

## Mirror Procedure (PKB → Native)

Invoked by `/pull` claim step.

1. Fetch the PKB task and its children:
   ```json
   parent = mcp__pkb__get_task(id="<pkb-id>")
   leaves = mcp__pkb__get_task_children(id="<pkb-id>")
   ```
2. Create the parent native task:
   ```json
   TaskCreate(
     subject="<short-title>",
     description="PKB <pkb-id> — <full-title>",
     activeForm="Implementing <subject>"
   )
   ```
3. For each child task in `leaves`, create a native task and block the parent:
   ```json
   child_native = TaskCreate(
     subject="<child-title>",
     description="PKB <child-id> — <child-title>",
     activeForm="Implementing <child-title>"
   )
   TaskUpdate(taskId=child_native, addBlocks=[parent_native_id])
   ```
4. Flipped parent native task to `in_progress`:
   ```json
   TaskUpdate(taskId=parent_native, status="in_progress")
   ```

## Per-Completion Sync (Native → PKB)

Execute immediately when setting a native task to `completed`:

1. Flipped status:
   ```json
   TaskUpdate(taskId="<native-id>", status="completed")
   ```
2. Read task details:
   ```json
   nt = TaskGet(taskId="<native-id>")
   ```
3. Parse the `PKB <id>` prefix from `nt.description`.
4. If the ID matches the bound parent, skip (handled by `/end_session`).
5. Otherwise, call:
   ```json
   mcp__pkb__complete_task(id="<pkb-id>", summary="<native-subject>")
   ```

## Final Reconciliation

Invoked during `/end_session` before calling `release_task`.

1. Call `tasks = TaskList()`.
2. Parse `PKB <id>` from `description` for all tasks.
3. For each native task marked `completed` whose PKB ID is NOT the bound parent:
   - Check PKB status using `mcp__pkb__get_task(id="<pkb-id>")`.
   - If not in a terminal state, call `mcp__pkb__complete_task(id="<pkb-id>", summary="reconciled at session close")`.

## Multi-Pull Cleanup

If `/pull` is run again in the same session, cancel the prior parent native task before mirroring the new task:

```python
tasks = TaskList()
for t in tasks:
    if t.status == "in_progress" and t.description.startswith("PKB <previous-pkb-id>"):
        TaskUpdate(taskId=t.id, status="deleted")
```

## Failure Recovery

| Symptom                                         | Cause                 | Recovery                                                   |
| :---------------------------------------------- | :-------------------- | :--------------------------------------------------------- |
| `TaskCreate` errors with "tool not loaded"      | Bootstrapping skipped | Run `ToolSearch` first.                                    |
| Native task lacks `PKB <id>`                    | Bypassed mirror step  | Treat as session-local task; do not sync.                  |
| `complete_task` fails with terminal state error | Row already updated   | Ignore and continue.                                       |
| Sync call failed mid-session                    | Server disconnect     | Final reconciliation at session close will correct status. |
| Native task cancelled (`deleted`)               | Task aborted          | Do not sync to PKB.                                        |

## Platform Scope

This skill is exclusive to the cowork build of `aops-core`. Keep files clean of other platform references.
