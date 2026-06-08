---
name: daily
type: skill
category: instruction
description: Daily note lifecycle — compose and maintain a factual daily note. Reports the state of the day; does not prioritise or recommend. SSoT for daily note structure.
triggers:
  - "daily list"
  - "daily note"
  - "morning briefing"
  - "update daily"
  - "daily update"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Read,Bash,Grep,Write,Edit,AskUserQuestion,Skill,mcp__pkb__delete,mcp__pkb__get_task,mcp__pkb__list_tasks,mcp__pkb__task_summary,mcp__pkb__complete_task
owner: pauli
version: 5.0.0
permalink: skills-daily
---

# Daily Note

Compose and maintain the daily note at `$ACA_DATA/daily/YYYYMMDD-daily.md` (filename uses today's date, `date +%Y%m%d`). On every run, point the symlink at it: `ln -snf daily/YYYYMMDD-daily.md $ACA_DATA/daily.md`.

Fill out the template in `references/note-template.md`. That file is the structural SSoT — follow its section order.

## What this note is

A factual, reportive snapshot of the day: what happened, what's open, what's due, what's in the inbox. It is **not** prescriptive — never rank what the user should do next or suggest a sequence. Forward prioritisation is the user's, in `### My priorities` (create the empty heading; never write under it).

## Core rules

- **Update throughout the day.** Re-run freely; update in place with Edit, not full rewrites. Consolidate where it helps readability.
- **Never remove user notes.** Preserve everything the user wrote, plus their ticks (`[x]`) and annotations, across regenerations. Match items by ID/PR/subject and carry ticks forward.
- **You may turn user notes into neat, well-formatted prose** — but only if you lose no truth. When unsure, keep the original wording.
- **No empty sections.** Omit a section rather than render an empty heading. On a morning with no sessions yet, omit Today's Log entirely.

## Tools you may invoke

Available, not mandatory steps. Use them when the day's content calls for them:

- `/email --daily` — triage the inbox into tasks + FYI items.
- `/q` — capture a task (e.g. routing a mobile capture from `$ACA_DATA/notes/mobile-captures/`; delete the original with `mcp__pkb__delete` once it's routed).
- `/remember` — persist durable knowledge.
- `/decision-extract` — expand the pending-decisions list if the user wants detail.
- `/strategy` — if the user signals they want a priorities reset.

## Safety rules (load-bearing)

- **Verify carryover against live PKB before listing.** For each task carried from yesterday, call `mcp__pkb__get_task`; drop it if it's missing, `done`, `cancelled`, or already ticked in today's note. Copying blindly produces phantom-overdue items.
- **Consume `$AOPS_SESSIONS/state/pr-state.json` for PR state; do NOT run `gh pr list`.** `repo-sync-cron` is the single producer. Path discovery — try in order:
  1. **Primary**: `$AOPS_SESSIONS/state/pr-state.json` (env var path).
  2. **Fallback**: if the primary is missing, run `grep -E '^export AOPS_SESSIONS=' ~/.env.local 2>/dev/null` to extract the `.env.local` value. If it differs from `$AOPS_SESSIONS`, check `<env_local_value>/state/pr-state.json`.
  3. **If artefact found via fallback**: use it, and emit one visible warning line in the note: `⚠️ pr-state read from <fallback_path> — $AOPS_SESSIONS env var is stale (current: <env_value>; .env.local: <env_local_value>). Update your shell env.`
  4. **If neither path yields a fresh (≤24h) artefact**: render one inline note naming both paths tried — never fall back to live `gh`.
  5. Always log which resolved path was used.
- **Consequence text is printed verbatim, never paraphrased.** Pull it from the task, or from a linked target in the task's `goals` field.
- **Counts come from `mcp__pkb__task_summary`.** Never count tasks yourself — aggregation is the PKB's job.

## Escalated deadlines (simple rule)

Hoist a due task into a `## 🚨 ESCALATED DEADLINES` callout when it meets any of these conditions:

- **Overdue** (past due date) AND ≥ SEV2; or
- **Due within ~2 days** AND ≥ SEV3; or
- **Due within ~2 days** AND ≥ SEV2 AND on an immovable external deadline.

Render its verbatim consequence text; drop it from the Status deadline list to avoid duplication. Do not hoist movable SEV2 tasks unless they are also overdue — that is false urgency inflation. Do not compute tiers or ratios — the full escalation model lives in `[[importance-visibility-escalation]]`, and a follow-up PKB-tool task will compute a real escalation tier upstream.

## Reconcile and cross-link

- When a merged PR or sent email is **clear** evidence that a `merge_ready`/`review` task is done, complete it (`mcp__pkb__complete_task`) with the evidence URL. Surface ambiguous cases under "Needs your call" — never auto-close on doubt.
- You may append a `## Progress` note or tick checklist items on the task a day's accomplishment maps to. Never mark a parent task done, never delete task content.

## Output

End with a one-line confirmation: "Daily note updated. Use `/pull` to start work." Then halt.
