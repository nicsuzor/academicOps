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
version: 5.3.0
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

### Task completion sweep (required every run)

Enumerate the **whole** parked backlog and resolve each task's PR against **live GitHub** — not a pre-baked feed. (Why live, not the feed: `pr-state.json`'s `recent_merged` is a recent-window snapshot; a task whose PR merged outside that window never matches and stays silently parked. The canonical reconcile contract is `[[workflows-reconcile]]` — structured fields drive the match, live `gh` confirms the state.)

1. **Fetch the parked task list.** Call `mcp__pkb__list_tasks(status="merge_ready")` and `mcp__pkb__list_tasks(status="review")`. Collect every result from both calls. This is the full candidate set — do not spot-check or keyword-search a subset.

2. **Resolve each task's PR from its structured fields** (no prose parsing — this is the `[[workflows-reconcile]]` "guaranteed structured" surface). For each task, in order:
   - `pr_url` frontmatter (e.g. `https://github.com/org/repo/pull/1859`) — the authoritative source; gives both repo (`org/repo`) and PR number.
   - `branch` frontmatter — resolve via `gh pr list --repo <repo> --head <branch> --state all --json number,state` when no `pr_url`.
   - A pure-integer tag (e.g. `1858`) — a PR number, but ambiguous without a repo; only usable once you know the task's repo (its `project`/repo field). Treat a bare number with no repo as unresolved.
   - If none resolve to a concrete `<repo>#<number>`, leave the task unchanged — it is not a reconcile candidate.

3. **Check live PR state per task.** For each resolved `<repo>#<number>`, run `gh pr view <number> --repo <repo> --json state,mergedAt,url`. Do this per task — the cost is one cheap call each and it is correct regardless of when the PR merged. Batch them in a single Bash loop if you like; do not substitute the feed's `recent_merged` list for this check.

4. **Act on the live state:**
   - **MERGED** → the task's own deliverable shipped: call `mcp__pkb__complete_task` with the PR URL and `mergedAt` in the evidence. No human confirmation needed — **except** the guards below.
   - **OPEN** → genuinely in-flight; leave parked (it is correctly `merge_ready`/`review`).
   - **CLOSED (not merged)** → the PR was rejected or abandoned; do NOT auto-close the task. Surface under "Needs your call" (refile-or-drop decision).
   - **No PR / not found** → leave unchanged.

5. **Guards (never violate — apply before any close):**
   - **Never close on doubt.** If the task body flags an unresolved condition (e.g. "an unauthorised edit must be stripped before merge", a pending live-host verification the worker cannot perform), surface it under "Needs your call" even when the PR shows MERGED.
   - **Never close a parent/epic that has open children.** Before closing, confirm the task is a leaf (or all its children are already `done`/`cancelled`). A merged parent PR with genuine open follow-up children is surfaced, not closed — do NOT cascade-close real downstream work. (A pure scope-note child the PR delivered may be closed recursively; a real independent follow-up task may not.)
   - **Never touch academic / peer-review / Nic-decision items.** Tasks that are inherently the user's call (peer reviews, funding assessments, design decisions awaiting his judgment) are surfaced, never auto-closed, regardless of any linked PR.

6. **Report.** In the daily note (Work Log or "What Needs Attention"): `N tasks auto-closed against merged PRs; M surfaced for your call (closed-without-merge / blocked-on-judgment / epic-with-open-children).`

### Cross-linking (when a session maps to a task)

You may append a `## Progress` note or tick checklist items on a task that today's accomplishment maps to. Never mark a parent task done, never delete task content.

## Output

Commit the note (don't leave it for the sync): `cd "$ACA_DATA" && git add "daily/$(date +%Y%m%d)-daily.md" daily.md && { git diff --cached --quiet || git commit -m "daily: note for $(date +%Y-%m-%d)"; }` — the guard makes no-op re-runs exit 0. If a pre-commit hook fails, let it surface; don't bypass it. Then end with a one-line confirmation: "Daily note updated. Use `/pull` to start work." and halt.
