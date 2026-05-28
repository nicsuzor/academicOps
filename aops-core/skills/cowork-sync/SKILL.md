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

# /cowork-sync: PKB ↔ native task list mirror

Cowork forces every session to drive work through the harness-native task list (`TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet`). The PKB remains the system of record across sessions, but inside a Cowork session the agent's working surface is the native list. This skill defines how the two stay aligned.

## Invariants

1. **PKB is the system of record.** Status, body, and follow-ups live in PKB across sessions. The native task list is a per-session working surface; it disappears when the session ends.
2. **PKB → native at claim.** When the bound PKB task is claimed (via `/pull`), mirror it onto the native list before any execution begins. Other claim paths (decompose-and-execute, supervisor tick) currently bypass this skill — see [[#scope]] below.
3. **Native is the agent's hands.** In-flight progress (start, in_progress, completed) goes through `TaskUpdate` on the native id. The agent does not bulk-update PKB mid-task; the only PKB writes during execution are the per-completion echoes described in invariant 4.
4. **Native → PKB on each completion.** The moment a native task is flipped to `status="completed"` (and that native task carries `PKB <id>` in its description), the same `TaskUpdate` call is paired with the matching PKB write — `mcp__pkb__complete_task` for a mirrored child, deferred to `release_task` in `/end_session` for the bound parent. This is the user-visible invariant: a child PKB row turns `done` the moment its native sibling is ticked off, not at session close.
5. **One-to-one mapping per session.** Each native task carries the PKB task id in its `description` (e.g. `"PKB task-acba1234 — Implement X"`). This is the join key for completion sync; without it the per-completion echo and the session-close reconciliation both no-op.

The native list is allowed to be ahead of PKB momentarily (the half-second between `TaskUpdate(status="completed")` and the paired `complete_task` call). PKB is allowed to be ahead of the native list when work was done outside Cowork. Beyond that brief window, the two stay in lockstep.

## Scope

This skill is invoked by `/pull` (claim path) and `/end_session` (final reconciliation). Other PKB-mutating skills inside a Cowork session — supervisor ticks, `/q`-style decompose-and-execute, ad-hoc agent calls that write directly to PKB — currently bypass the mirror. Their PKB writes will still take effect, but the native task list will not reflect them until the next `/pull` or `TaskList` refresh. If invariant 2 needs to broaden to cover those paths, the work is to add the same mirror call at the analogous claim point in each.

## Bootstrap

The Cowork harness presents `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` as deferred tools. Before the first call, load their schemas:

```
ToolSearch(query="select:TaskCreate,TaskUpdate,TaskList,TaskGet", max_results=4)
```

Skip this step if a previous call in the session already loaded them — the schemas persist for the session.

## Mirror procedure (PKB → native)

Called from `/pull` (Step 1.6 — Cowork only) and from any other skill that needs to surface a PKB task for execution.

Input: a PKB task id with body, AC, and optional children.

1. **Load task and children**:
   ```
   parent  = mcp__pkb__get_task(id="<pkb-id>")
   leaves  = mcp__pkb__get_task_children(parent_id="<pkb-id>")  # if non-leaf
   ```
2. **Create one native task for the parent** with a description that embeds the PKB id verbatim (it is the join key):
   ```
   TaskCreate(
     subject="<short title — first ~60 chars of PKB title>",
     description="PKB <pkb-id> — <full title>\n\n<one-line goal + AC anchor>",
     activeForm="<imperative present continuous — 'Implementing X'>"
   )
   ```
   Save the returned native task id (`#N`) — you will reference it via `TaskUpdate` for the rest of the session.
3. **If the PKB task has acceptance criteria as children**, mirror each child as a separate native task and set the parent's `addBlocks` (or each child's `addBlockedBy`) so the parent only unblocks once children complete:
   ```
   for child in leaves:
       child_native = TaskCreate(
           subject="<child title>",
           description="PKB <child-id> — <child title>",
           activeForm="<...>"
       )
       TaskUpdate(taskId=child_native, addBlocks=[parent_native_id])
   ```
   If the PKB task is a leaf or you intend to handle AC inline in the parent body, skip this step.
4. **Mark the parent native task `in_progress` immediately** to reflect that you have claimed it:
   ```
   TaskUpdate(taskId=parent_native, status="in_progress")
   ```
5. **Do NOT update PKB status here.** `/pull` has already set PKB status to `in_progress` and bound the task to the session via the binding file (see [[../../commands/pull.md]] Step 1.4). The PKB mid-session writes stop there.

## Per-completion sync (native → PKB, during the session)

Run this every time the agent flips a native task to `completed`. The rule is **one paired write per completion** — `TaskUpdate(status="completed")` immediately followed by the matching PKB write — so a future reader of the PKB graph sees the child task turn `done` at the same wall-clock moment the user sees the native checkbox flip.

```
TaskUpdate(taskId="<native-id>", status="completed")

# Read the native task to recover its PKB id from `description`
nt = TaskGet(taskId="<native-id>")
pkb_id = _parse_pkb_id(nt.description)   # extracts the id from "PKB <id> — …"
if pkb_id is None:
    return                               # ad-hoc native task, not mirrored from PKB
if pkb_id == "<bound-parent-pkb-id>":
    return                               # defer to /end_session's release_task call
mcp__pkb__complete_task(id=pkb_id, summary="<one-line, derived from native subject>")
```

Edge cases:

- **Already terminal in PKB.** `complete_task` rejects a row whose status is already `done`/`cancelled`/`superseded`/`archived`. Catch the error and continue; the desired state already holds.
- **Bound parent flipped to completed mid-session.** Don't echo it here — `/end_session` will call `release_task` against the bound id with the full session payload (PR, branch, summary). Echoing now would race the closing call.
- **Native parent with `addBlocks` children.** When the last child completes, the native parent will auto-transition out of `blocked` to whatever its prior state was. If the agent then ticks the parent to `completed`, the same paired-write rule applies — but typically the agent leaves the parent for `/end_session` rather than ticking it manually.
- **Cancelled, not completed.** A native task moved to `deleted` is the agent abandoning that working item; do NOT echo to PKB. PKB cancellation is a deliberate `update_task(status="cancelled")` decision and goes through `/end_session` or an explicit follow-up, not through native-list maintenance.

## Final reconciliation (native → PKB, at session close)

Called from `/end_session` Step 0.5 (Cowork only), before `release_task`. This is a safety net for the rare case where per-completion sync was skipped — a `TaskUpdate` was made without the paired PKB write, the per-completion code path errored silently, or the session is closing mid-thought with native completions that never made it back.

Input: the bound PKB task id (resolved by `/end_session` from the binding file) and the current state of the native task list.

1. **Read the native list**:
   ```
   tasks = TaskList()
   ```
2. **Match each native task to its PKB id** by parsing `PKB <id>` out of `description`. Native tasks with no PKB id in their description were created ad-hoc — leave them alone; they die with the session.
3. **For each native task with `status: completed` AND a PKB id that is NOT the bound parent**:
   - Call `mcp__pkb__get_task(id="<pkb-child-id>")` first to check status.
   - If the PKB row is already `done`/`cancelled`/`superseded`/`archived`, skip — per-completion sync already handled it.
   - Otherwise call `mcp__pkb__complete_task(id="<pkb-child-id>", summary="reconciled at session close")`. This is the safety net firing.
4. **For each native task still `in_progress` or `pending`**: do nothing. The supervisor or next `/pull` will pick them up; their PKB rows are still in the right state.
5. **The bound parent is always handled by `/end_session`'s `release_task` call**, regardless of its native state. Do not echo it here.
6. **Do NOT delete or rewrite native tasks.** The native list dies with the session — there is nothing to clean up.

## `/pull` invoked twice in the same session

`/pull` overwrites the binding file with the new task id (most-recent-claim-wins). The previously-mirrored native task is left in place. The agent SHOULD mark it cancelled before the new mirror call so the native list does not accumulate stale `in_progress` shells across re-pulls:

```
# Before mirroring the new claim, find and retire the prior native parent
tasks = TaskList()
for t in tasks:
    if t.status == "in_progress" and "PKB " in t.description and t.description.startswith("PKB <previous-pkb-id>"):
        TaskUpdate(taskId=t.id, status="deleted")  # native-only retirement; do NOT echo to PKB
```

The PKB row for the previous claim was already set back to `queued` (or wherever) by whatever logic released the prior task — that is not this skill's concern. Cowork-sync is responsible only for keeping the native list in sync; PKB state-machine transitions for re-pulls live in `/pull` / `release_task`.

## Failure modes (and what to do)

| Symptom                                                                                     | Cause                                                                            | Recovery                                                                                                                                                                                             |
| ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TaskCreate` errors with "tool not loaded"                                                  | ToolSearch bootstrap was skipped                                                 | Run the `ToolSearch(select:TaskCreate,…)` call from Bootstrap and retry.                                                                                                                             |
| Native task has no `PKB <id>` in `description`                                              | Mirror was bypassed, or the agent created a free-standing checklist item         | Treat as session-local working note. Do not echo to PKB at completion or at close.                                                                                                                   |
| Native task is `completed` but PKB row is already `done`                                    | Per-completion sync already ran, or task was completed externally between writes | No-op. `complete_task` on a terminal PKB row is rejected; catch the error and continue.                                                                                                              |
| Native task flipped to `completed` but the paired PKB write errored                         | Server transient, MCP disconnect mid-call, or PKB row in an unexpected state     | The session-close reconciliation in `/end_session` Step 0.5 catches the drift and retries. Don't re-flip the native task to recover; the safety net is the right repair surface.                     |
| Native parent is `in_progress` at session close but child tasks are `completed`             | Children done, parent body still has unmet AC                                    | Normal partial-completion case. Children were already echoed to PKB at completion; `/end_session` calls `release_task` on the parent with `status="merge_ready"` or `"blocked"` per its usual logic. |
| PKB has subtasks that were never mirrored (mirror happened before a later `decompose_task`) | Mirror is one-shot at claim, not continuous                                      | Acceptable. Newly-created PKB subtasks land in `queued` and will be picked up by the next `/pull`. Do not retroactively mirror.                                                                      |
| Native task cancelled (`deleted`) instead of completed                                      | Agent retired a working item without completing it                               | Do NOT echo to PKB. PKB cancellation is a separate decision that goes through `/end_session` or an explicit `update_task(status="cancelled")` — never piggybacked on a native deletion.              |

## Why this shape

- **Per-completion echo, not session-close batch.** The user's intent is that PKB reflects each task completion as it happens — so the dashboard, the supervisor, and concurrent readers see the leaf turn `done` the moment the agent ticks the native checkbox. Session-close batch sync was the earlier draft of this skill and is preserved as the safety net only; per-completion is the primary path.
- **Bound parent is the one exception.** The bound parent's completion needs the full `release_task` payload (PR, branch, summary, follow-ups) that `/end_session` assembles. Echoing it mid-session would race the closing call and lose the structured payload, so the parent is deliberately deferred.
- **Native list disappears at session end.** Treating it as authoritative would erase work. PKB is the only durable surface; the native list is a working surface bolted on top.
- **Cowork's harness forces native-list use.** Hooks and Python helpers are silently dropped; the only reliable signal to the harness that "I'm working on X" is `TaskUpdate(status="in_progress")`. Skills that don't mirror lose the affordance the harness gives for free.

## Non-cowork platforms

This skill ships ONLY in the cowork build of aops-core. The same source file is excluded by `scripts/build.py` for `claude`, `gemini`, and `antigravity` platforms — there is no native-list equivalent on those surfaces, and the PKB CLI / MCP suffices on its own.
