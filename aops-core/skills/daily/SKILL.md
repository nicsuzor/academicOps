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
version: 5.4.0
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
- **Today's Log is reconstructed from primary sources, never substituted.** Before writing Today's Log you MUST open today's session transcripts — `$AOPS_SESSIONS/transcripts/$(date +%Y-%m)/$(date +%Y%m%d)-*-claude-*.md` (prefer `-abridged.md`) — and reconstruct the day from them. Assembling it from artifacts already in the note (prior retro stamps, yesterday's log) or from the reconcile sweep's merged-PR list is a criterion substitution: it reproduces the file, not the day. If no same-day interactive transcript exists, omit the section — do not back-fill it from second-hand artifacts.

## Tools you may invoke

Available, not mandatory steps. Use them when the day's content calls for them:

- `/email --daily` — triage the inbox into tasks + FYI items.
- `/q` — capture a task (e.g. routing a mobile capture from `$ACA_DATA/notes/mobile-captures/`; delete the original with `mcp__pkb__delete` once it's routed).
- `/remember` — persist durable knowledge.
- `/decision-extract` — expand the pending-decisions list if the user wants detail.
- `/strategy` — if the user signals they want a priorities reset.

## Safety rules (load-bearing)

- **Verify carryover against live PKB before listing.** For each task carried from yesterday, call `mcp__pkb__get_task`; drop it if it's missing, `done`, `cancelled`, or already ticked in today's note. Copying blindly produces phantom-overdue items.
- **PR display state may read `$AOPS_SESSIONS/state/pr-state.json`** for the "Outstanding Workflows" / open-PR snapshot (it is cheap and good enough for a display list). Do NOT run a bulk `gh pr list` just to populate that display. The reconcile sweep below is the exception: it resolves and checks PRs **one task at a time against live `gh`**, because a pre-baked feed's recent-window misses older merges and silently leaves tasks parked.
- **Consequence text is printed verbatim, never paraphrased.** Pull it from the task, or from a linked target in the task's `goals` field.
- **Counts come from `mcp__pkb__task_summary`.** Never count tasks yourself — aggregation is the PKB's job.

## Escalated deadlines (simple rule)

Hoist a due task into a `## 🚨 ESCALATED DEADLINES` callout when it meets any of these conditions:

- **Overdue** (past due date) AND ≥ SEV2; or
- **Due within ~2 days** AND ≥ SEV3; or
- **Due within ~2 days** AND ≥ SEV2 AND on an immovable external deadline.

Render its verbatim consequence text; drop it from the Status deadline list to avoid duplication. Do not hoist movable SEV2 tasks unless they are also overdue — that is false urgency inflation. Do not compute tiers or ratios — the full escalation model lives in `[[importance-visibility-escalation]]`, and a follow-up PKB-tool task will compute a real escalation tier upstream.

## Reconcile and cross-link

### Two statuses, two fates — do not conflate them

- **`status: merge_ready` = parked on a PR.** Under review — PR open, awaiting CI, review, or iteration ([[taxonomy#status-values-and-transitions]] is the SSoT for the full protocol). The PR is the source of truth for whether it can close.
- **`status: review` = parked on a human.** Actionable work waiting on Nic's (or an agent's) judgment, not on a merge ([[taxonomy#status-values-and-transitions]]). Most `status: review` tasks have no PR at all — reading notes, design decisions, "needs Nic's direction" items.

**Never auto-close a `review` task.** Its close is always a decision, never a PR match — even a PR showing MERGED is evidence, not authority. Surface every `review` task under "Needs your call" every run; it must never silently disappear as if it were parked PR backlog.

### Task completion sweep (required every run)

Resolve PRs against **live GitHub**, not the pre-baked `pr-state.json` feed — its `recent_merged` is a recent-window snapshot and misses older merges. The canonical reconcile contract is `[[workflows-reconcile]]`: structured fields (`pr_url`, else `branch`, else a repo-qualified PR number) drive the match, `gh` confirms the state.

For each `merge_ready` task: resolve its PR and check the live state. MERGED closes the task (`mcp__pkb__complete_task`, citing the PR URL and merge time as evidence). OPEN leaves it parked. CLOSED-without-merge, or unresolvable to a concrete `<repo>#<number>`, is surfaced under "Needs your call" instead of auto-closed.

For each `review` task: resolve any linked PR the same way, but its state is evidence only, never grounds for a close — surface it regardless, with its title and one-line ask. A `review` item with no actionable ask at all (e.g. a reading note that was never really a task) is surfaced as mis-statused so Nic can re-file or drop it.

**Guards, both passes:** never close on doubt (an unresolved condition flagged in the task body beats a MERGED PR); never cascade-close a parent whose children are still open; never touch academic, peer-review, or Nic-decision items — these are always surfaced, never auto-closed.

**Report** in the daily note: tasks auto-closed against merged PRs, `review` tasks re-surfaced awaiting a decision, tasks surfaced for a call.

### Cross-linking (when a session maps to a task)

You may append a `## Progress` note or tick checklist items on a task that today's accomplishment maps to. Never mark a parent task done, never delete task content.

## Output

Commit the note (don't leave it for the sync): `cd "$ACA_DATA" && git add "daily/$(date +%Y%m%d)-daily.md" daily.md && { git diff --cached --quiet || git commit -m "daily: note for $(date +%Y-%m-%d)"; }` — the guard makes no-op re-runs exit 0. If a pre-commit hook fails, let it surface; don't bypass it. Then end with a one-line confirmation: "Daily note updated. Use `/pull` to start work." and halt.
