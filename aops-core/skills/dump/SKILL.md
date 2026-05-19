---
name: dump
type: skill
category: instruction
description: Emergency session bail — fast resume task + short handover, no commit/PR/reflection. For when you (or the user) need a clean context now. Use /end-session for canonical close.
triggers:
  - "emergency handoff"
  - "emergency handover"
  - "bail"
  - "dump"
  - "out of context"
  - "context full"
  - "need clean context"
  - "interrupted, need to restart"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
permalink: skills/dump
---

# /dump: emergency handover (fast bail)

For when you (or the user) need a clean session **now** and do not want to commit, push, file a PR, or write reflection blocks. The full canonical close is `/end-session`.

The goal of this skill is **a resume-ready task and a short handover block**, in as few tool calls as possible. Uncommitted work stays on the branch as-is. The supervisor and the next session pick it up from the task body.

## When to use this vs /end-session

- **/dump** — context window is full, user said "dump and restart", agent is wedged, work is mid-flight and not in a committable state. Output: a resume task + one-screen handover.
- **/end-session** — task is complete (or terminally blocked), normal end-of-day, autonomous/headless close. Full quality bar: commit, push, PR, `release_task`, reflection blocks.

If the bound task is genuinely complete, do **not** use /dump — use /end-session.

## Execution

1. **Write a resume delta to the task.** Call `mcp__pkb__update_task` on the bound task:

   - Set `session_id` to `$AOPS_SESSION_ID` if not already set. Do not mutate any other frontmatter; do not change `status`.
   - Append to the task body a `## Resume <UTC-timestamp>` section containing:
     - **State**: one sentence on where things are (what is done, what is in flight).
     - **Next**: the single next concrete action to pick up.
     - **Watch out**: any in-flight side-effects (uncommitted files, running processes, half-applied migrations, modified remote state, locks held). One line per item.

   If no task is bound, call `mcp__pkb__create_task` with a one-sentence title, the resume content as the body, and `parent="adhoc-sessions"` (the default catch-all parent for resume/handover tasks), then proceed.

2. **Emit the handover block.** Exactly this shape, no prose before or after:

   ```markdown
   ### Emergency Handover

   - **Session ID**: `$AOPS_SESSION_ID`
   - **Resume Task**: `<task-id>` (<short title>)
   - **Branch**: `<branch>` (uncommitted: yes/no)
   - **Next**: <one line: what to do first in the new session>
   ```

3. **Halt.** Nothing follows the block.

## What this skill does NOT do

- Does **not** commit, push, or create a PR. Work in flight stays on the branch.
- Does **not** call `release_task` or change task status. The supervisor sees the task still `in_progress` — that is intentional; the work is resuming.
- Does **not** emit `## Framework Reflection`, `## Output`, or `## Tasks worked`. Those belong to /end-session.
- Does **not** verify environment state (container health, disk space, deploy status, test runs). If validation matters, it goes in the **Watch out** field so the next session knows to check.
- Does **not** loop on itself. If the gate reopens after further mutating tool calls, run `/dump` again.
