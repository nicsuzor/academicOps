---
name: dump
alias: end_session
type: skill
category: instruction
description: Complete session handover. Interactive sessions can use the short-form branch (task delta + follow-up); full sessions use the standard path (commit + push + PR + release_task + halt).
triggers:
  - "emergency handoff"
  - "save work"
  - "handover"
  - "interrupted"
  - "session end"
  - "close session"
  - "wrap up"
  - "session complete"
  - "stop hook blocked"
modifies_files: true
needs_task: true
mode: execution
domain:
  - operations
permalink: skills/dump
---

# /dump: session close and handover

Close a work session cleanly. This skill supports two paths:

1. **Short-form** (Interactive only): For when you've done a small amount of work and the user is still steering.
2. **Full-form** (Standard): For the normal end-of-session path, or for special-case handovers (emergency, cross-machine, interrupted).

## Contract

Per [[session-handover-contract]]:

- **Full-form** terminal output is a terse 5–10 line markdown block in a strict parseable format.
- **Short-form** output is a simple next-step statement.
- Structured session data lives in the task's YAML frontmatter, written by `release_task` (Full) or `update_task` (Short).
- `$AOPS_SESSION_ID` is the join key that groups session artifacts.

## Execution

1. **Branch decision**.
   - **Short-form** (Interactive only): If you have a clear next-step follow-up (e.g., more work remains on the task, or you are blocked on external input) and the user is still steering the conversation, use the **Short-form** branch.
   - **Full-form** (Default): If the task is complete, or you are truly ending the session (e.g., end-of-day, long-running task complete), use the **Full-form** branch.

### Short-form Branch (Interactive)

1. **Update the task**. Write the latest delta (what was just done, what is left) to the task body using `update_task`.
2. **Present follow-up**. Output a one or two-line summary: "Next: [X]" or "Blocked on: [Y]".
3. **Finish**. Do NOT emit the handover block or halt. The gate is satisfied for this turn.

### Full-form Branch (Standard)

1. **Commit, push, file PR**. If file changes exist, commit them, push the branch, and run `gh pr create --fill`. If no file changes, skip. Never end a session with uncommitted work.

2. **Call `release_task` once, with the full session payload.**

   ```
   mcp__pkb__release_task(
     id="<task-id>",
     status="merge_ready" | "review" | "done" | "blocked",
     session_id="$AOPS_SESSION_ID",
     pr_url="https://github.com/...",         # omit if no PR
     branch="<branch-name>",
     issue_url="https://github.com/.../issues/...",  # omit if none
     follow_up_tasks=["task-xxxx", "task-yyyy"],     # task IDs only; must exist
     release_summary="<one sentence, result-oriented, <= 500 chars>"
   )
   ```

   - **No task bound?** `release_task` auto-creates a minimal ad-hoc task under the `adhoc-sessions` root ([[T4]]). Until T4 lands, fall back to `create_task` first, then `release_task` on the new id.
   - **`release_summary` quality**: result-oriented ("Implemented YAML schema extension for session handover"), not activity-oriented ("I worked on the schema"). This is the primary signal for the Recent Sessions dashboard.
   - **Follow-ups**: every concrete future action must be a real PKB task before you list it here. Do not put bullet prose into `release_summary` or session notes — the dashboard and `/recap` only see structured fields.
   - **Fallback**: if `release_task` is unavailable, `update_task(id=..., status="merge_ready")` keeps the supervisor unblocked, but the dashboard loses this session.
   - **Polecat note**: calling `release_task` with a terminal status is what lets the polecat supervisor detect termination via PKB polling. Skipping this leaves Gemini workers running until external timeout (#521).

3. **Emit the handover block**. Exactly this shape, 5–10 lines:

   ```markdown
   ### Session Handover

   - **Session ID**: `$AOPS_SESSION_ID`
   - **Primary Task**: `<task-id>` (<short title>)
   - **PR**: <url>
   - **Branch**: `<branch>`
   - **Issue**: <url or "none">
   - **Follow-ups**: `<task-id>`, `<task-id>` (or "none")
   - **Summary**: <release_summary value>
   ```

   Omit `PR` and `Issue` lines if not set. Omit `Follow-ups` if empty. Do not add any prose before or after the block.

4. **Halt.** Nothing follows the handover block.

## What this skill does NOT do

- Does **not** persist discoveries to memory, codify learnings, or file GitHub issues. Those are separate skills ([[remember]], [[learn]]) and belong in the session body, not the close.
- Does **not** loop on itself. If the gate reopens after further edits, run `end_session` again.
