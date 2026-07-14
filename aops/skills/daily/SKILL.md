---
name: daily
description: "Daily note lifecycle \u2014 compose and maintain a factual daily note.\
  \ Reports the state of the day; does not prioritise or recommend. SSoT for daily\
  \ note structure."
context: fork
agent: pauli
---

# Daily Note

Compose and maintain the daily note at `$ACA_DATA/daily/YYYYMMDD-daily.md` (filename uses today's date, `date +%Y%m%d`). On every run, point the symlink at it: `ln -snf daily/YYYYMMDD-daily.md $ACA_DATA/daily.md`.

Fill out the template in `references/note-template.md`. That file is the structural SSoT — follow its section order.

## What this note is

A factual, reportive snapshot of the day: what happened, what's open, what's due, what's in the inbox. It is **not** prescriptive — never rank what the user should do next or suggest a sequence. Forward prioritisation is the user's, in `### My priorities` (create the empty heading; never write under it).

## Core rules

- **Frontmatter MUST set `type: daily`.** This is the canonical-path derivation key: the storage path is derived from this field alone, so a note written or regenerated without it is misfiled by definition. Verify the field is present before the first write and after every regeneration; never let a fallback path (e.g. `type: note`) stand in silently.
- **Update throughout the day.** Re-run freely; update in place with Edit, not full rewrites. Consolidate where it helps readability.
- **Never remove user notes.** Preserve everything the user wrote, plus their ticks (`[x]`) and annotations, across regenerations. Match items by ID/PR/subject and carry ticks forward.
- **You may turn user notes into neat, well-formatted prose** — but only if you lose no truth. When unsure, keep the original wording.
- **No empty sections.** Omit a section rather than render an empty heading. On a morning with no sessions yet, omit Today's Log entirely.
- **Today's Log is reconstructed from primary sources, never substituted.** Before writing Today's Log you MUST open today's session transcripts — `$AOPS_SESSIONS/transcripts/$(date +%Y-%m)/$(date +%Y%m%d)-*-claude-*.md` (prefer `-abridged.md`) — and reconstruct the day from them. Assembling it from artifacts already in the note (prior retro stamps, yesterday's log) or from the reconcile sweep's merged-PR list is a criterion substitution: it reproduces the file, not the day. If no same-day interactive transcript exists, omit the section — do not back-fill it from second-hand artifacts.
- **Prompt Ledger is generated, never hand-transcribed.** If `$AOPS_SESSIONS/state/prompt_ledger.md` is missing or stale (not regenerated today), refresh it: `uv run python aops-core/scripts/transcript.py --ledger --since <7-days-ago>` from the academicOps checkout. Tail its most recent ~10 lines into `## Prompt Ledger` verbatim. Never write ledger lines by hand and never fill in a blank outcome/link yourself — they're blank because the pipeline couldn't honestly resolve them from the session summary, not because the field was skipped.

## Tools you may invoke

Available, not mandatory steps. Use them when the day's content calls for them:

- `/email --daily` — triage the inbox into tasks + FYI items.
- `/q` — capture a task (e.g. routing a mobile capture from `$ACA_DATA/notes/mobile-captures/`; delete the original with `mcp__services__pkb__delete` once it's routed).
- `/remember` — persist durable knowledge.
- `/decision-extract` — expand the pending-decisions list if the user wants detail.
- `/strategy` — if the user signals they want a priorities reset.

## Safety rules (load-bearing)

- **Verify carryover against live PKB before listing.** For each task carried from yesterday, call `mcp__services__pkb__get_task`; drop it if it's missing, `done`, `cancelled`, or already ticked in today's note. Copying blindly produces phantom-overdue items.
- **PR display state may read `$AOPS_SESSIONS/state/pr-state.json`** for the "Outstanding Workflows" / open-PR snapshot (it is cheap and good enough for a display list). Do NOT run a bulk `gh pr list` just to populate that display. The reconcile sweep below is the exception: it resolves and checks PRs **one task at a time against live `gh`**, because a pre-baked feed's recent-window misses older merges and silently leaves tasks parked.
- **Consequence text is printed verbatim, never paraphrased.** Pull it from the task, or from a linked target in the task's `goals` field.
- **Counts come from `mcp__services__pkb__task_summary`.** Never count tasks yourself — aggregation is the PKB's job.

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

For each `merge_ready` task: resolve its PR and check the live state. MERGED closes the task (`mcp__services__pkb__complete_task`, citing the PR URL and merge time as evidence). OPEN leaves it parked. CLOSED-without-merge, or unresolvable to a concrete `<repo>#<number>`, is surfaced under "Needs your call" instead of auto-closed.

For each `review` task: resolve any linked PR the same way, but its state is evidence only, never grounds for a close — surface it regardless, with its title and one-line ask. A `review` item with no actionable ask at all (e.g. a reading note that was never really a task) is surfaced as mis-statused so Nic can re-file or drop it.

**Guards, both passes:** never close on doubt (an unresolved condition flagged in the task body beats a MERGED PR); never cascade-close a parent whose children are still open; never touch academic, peer-review, or Nic-decision items — these are always surfaced, never auto-closed.

**Report** in the daily note: tasks auto-closed against merged PRs, `review` tasks re-surfaced awaiting a decision, tasks surfaced for a call.

### Stale-claim & ready-queue reconcile (required every run)

This catches claims made and then silently dropped, and stale premises on tasks nobody has tried to select since they went stale. **Owned here, not in `/sleep`**: `/daily` fires on Nic's actual cold-open cadence, whereas cron and `/sleep`'s own loop are known-unreliable — a reconcile that lives only where it might not fire closes no loops. This **complements, does not replace**, `/sleep`'s longer-horizon staleness and artifact-rot checks; do not re-implement those here.

**Stale-claim pass.** `mcp__services__pkb__list_tasks(status="in_progress", before=<today - 2 days>, format="json")` (cap 30/run). For each candidate:

- If `type` is `epic` or the task has children (a parent task spanning multi-session work), skip it this run unless it has _also_ been untouched for ≥14 days — 2 days of quiet on a container task is normal, not abandonment.
- Skip any task whose body reads as a live Nic-led TALK/interactive session (explicit "waiting on Nic being live" / "do not dispatch to a worker" framing, or similar) — those are meant to sit `in_progress` across sessions; a long gap is not abandonment.
- Otherwise read the body and check for completion evidence (linked PR merged, a commit referencing the task ID, a same-day transcript closing statement). Decide exactly one:
  - **(a) Completed** — evidence found → `mcp__services__pkb__complete_task(id, completion_evidence="<what was found>", pr_url=<if any>)`.
  - **(b) Abandoned, premise still valid** — no completion evidence and nothing in the body says the work is no longer wanted → `mcp__services__pkb__update_task(id, updates={status: "queued", assignee: null})`, then `mcp__services__pkb__append(id, content="Released by /daily stale-claim reconcile YYYY-MM-DD: in_progress since <date>, no activity or completion evidence found — returned to queue for redispatch.")`. Return it to `queued` — the state it was dispatched from, already past the premise gate — never promote it further.
  - **(c) Premise gone or superseded** — the body shows the goal no longer applies (superseded, overtaken by a sibling, or blocked on something since resolved a different way) → do **not** cancel or delete. `mcp__services__pkb__update_task(id, updates={needs_triage: true})`, then `mcp__services__pkb__append(id, content="Flagged by /daily stale-claim reconcile YYYY-MM-DD: premise appears superseded/gone — <one-line reason>. Needs a human close, not auto-cancel.")`.

**Ready-queue premise pass.** Runs once per calendar day, not every `/daily` invocation (guard: skip if `$ACA_DATA/state/ready-queue-reconcile-cursor.json` already records today's date; write today's date after running). `mcp__services__pkb__list_tasks(status="ready", before=<today - 2 days>)` and `mcp__services__pkb__list_tasks(status="queued", before=<today - 2 days>)` (cap 30 each). For each candidate, check the two signals the point-of-claim gate can only catch when a select is actually attempted:

1. **`superseded_by` set but status is still `ready`/`queued`** — should have moved to `cancelled` at supersession time and didn't.
2. **All siblings under the same parent are `done`/`cancelled`** (via `mcp__services__pkb__get_task_children` on the parent) and this task's body reads like it belonged to the same finished batch — likely a leftover from a completed decomposition.

Artifact-existence rot (named file/symbol no longer present) is **not** re-checked here — that stays `/sleep`'s job. For every match: `mcp__services__pkb__append(id, content="Flagged by /daily ready-queue reconcile YYYY-MM-DD: <reason>. Left as-is for human review.")`. Flag, never hard-delete or auto-cancel.

**Report** in the daily note: one summary line in `## Work Log` (`Stale-claim reconcile: N closed, M released, K flagged. Ready-queue reconcile: J flagged.`) plus every flagged item (both passes) listed under "Needs your call" in `## What Needs Attention`, with task ID and the one-line reason.

### Cross-linking (when a session maps to a task)

You may append a `## Progress` note or tick checklist items on a task that today's accomplishment maps to. Never mark a parent task done, never delete task content.

## Output

Commit the note (don't leave it for the sync): `cd "$ACA_DATA" && git add "daily/$(date +%Y%m%d)-daily.md" daily.md && { git diff --cached --quiet || git commit -m "daily: note for $(date +%Y-%m-%d)"; }` — the guard makes no-op re-runs exit 0. If a pre-commit hook fails, let it surface; don't bypass it. Then end with a one-line confirmation: "Daily note updated. Use `/pull` to start work." and halt.
