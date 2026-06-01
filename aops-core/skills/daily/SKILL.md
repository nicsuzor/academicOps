---
name: daily
type: skill
category: instruction
description: Daily note lifecycle - briefing and progress sync. Reports the state of the day; does not prioritise or recommend. SSoT for daily note structure.
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
allowed-tools: Read,Bash,Grep,Write,Edit,AskUserQuestion,Skill,mcp__pkb__delete,~~email
owner: pauli
version: 4.1.0
permalink: skills-daily
---

# Daily Note Skill

Compose and maintain a daily note that **reports** the state of the day to the user. The note is a factual briefing — what's in the inbox, what's on the calendar, what's due, what's open, what ran. It does **not** curate, rank, recommend, or suggest sequences.

Location: `$ACA_DATA/daily/YYYYMMDD-daily.md`

**Always anchor on today's calendar date first.** Before writing anything, run `date +%Y-%m-%d` and `date +%A` and use those values for the note filename, the title's day-of-week label, and every relative-day phrase ("tomorrow", "2d", "next Mon"). Do not derive the day-of-week from session-activity dates, last-modified timestamps, or yesterday's note — those will mislead you whenever the morning has no activity. The note for `YYYYMMDD-daily.md` is for that calendar date, full stop.

**Work date ≠ calendar date.** End-of-day summaries and reflections target the **work-date** note — the note for the day being described — not today's note. A reflection written at 01:30 on 2026-04-23 about 2026-04-22's work lands in `20260422-daily.md`. See [[instructions/reflect]] Step 0 and [[instructions/work-summary]] §"Work date vs. calendar date".

**Do not backfill yesterday's narrative into today's note.** When `/daily` runs in the morning and today has no session activity yet, the work date for any narrative you generate is _yesterday_ (or earlier) — and that narrative must land in _yesterday's_ note, not today's. Today's note gets the empty-morning treatment: omit `## Today's Log` entirely, leave Work Log with "No PRs merged yet today". The most common failure mode of this skill is writing yesterday's PR-merge wave into today's note while mislabelling the day-of-week — guard against it explicitly.

**But when today HAS session activity, render `## Today's Log` in Morning Timeline mode** — a chronological narrative anchored on the user's verbatim prompts that answers "what was I just trying to do?" for a user returning to their desk after a context switch. See [[instructions/morning-timeline]]. This is the most useful artefact in a mid-day `/daily` and must not be skipped because the day isn't over.

## Purpose

The daily note answers two questions for a knowledge worker returning to their desk:

1. **What's the state of my world?** — Deadlines, inbox, open threads, calendar
2. **What happened?** — A factual log of sessions, merged PRs, and completed tasks

Prioritisation is the user's job. The agent's job is to surface facts accurately so the user can decide. The skill has no authority to weight tasks by significance, recommend what to work on, or suggest sequences — it has not been in the room for the human conversations that determine real priority, and guessing is worse than silence.

The note is a _reporting_ document, not an execution trigger. After the note is updated, output "Daily note updated. Use `/pull` to start work." and HALT.

## Quality Criteria

A good daily note is evaluated qualitatively:

- **Scannable in 30 seconds**: The user can glance at the note and see deadlines, new inbox items, and what's open. No hunting.
- **Factual on state; editorial on history.** Reporting _what exists right now_ — deadlines, inbox, open threads, calendar — is factual: list the items, don't rank them. Reporting _what happened_ — the shape of past work — is editorial: the agent is a smart synthesist who names patterns, connects threads across days, surfaces silences, and writes with proportional detail. The target is insight per sentence, not coverage per session. A row-for-row transcript of what ran is a failure mode; so is a verdict on what the user should do next.
- **Actions linked to tasks**: Every actionable item references its task ID. Every email item that needs a response has a corresponding task created or updated in the PKB. Information captured but not persisted is information lost.
- **Nothing lost**: Email items that need responses have tasks. Carryover is verified against live task state (no phantom overdue). User annotations are preserved.
- **No ranking of what's next**: Do not categorise upcoming work as SHOULD/DEEP/ENJOY/QUICK/UNBLOCK. Do not suggest sequences or say "start with X because Y". This applies to _forward_ prioritisation; narration of past work is governed by the editorial criterion above.

## Invocation

Every `/daily` invocation updates the note in place. The skill is designed to be run repeatedly throughout the day. There are no separate modes.

```
/daily          # Update the note (create if missing)
/daily sync     # Alias for muscle memory
```

## Note Structure

The daily note has **five sections**, each serving a distinct purpose.

Sections appear in this order: **Carryover → Status → What Needs Attention → Today's Log → Work Log**.

### 1. Carryover

Items carrying forward from yesterday and end-of-day abandoned todos. Each item is a checkbox (`- [ ] [task-id] Title`) so the user can tick it off.

**Live-state verification step (P#26 Verify First):** Before carrying any factual claim from a prior daily note (GitHub issue state, deployed-vs-undeployed, blocked-vs-unblocked), you MUST verify against live state. Never copy blindly from yesterday's note. Specifically: any prior-day claim that names a GitHub issue or PR must be re-checked via `gh issue view` or `gh pr view` before being re-asserted in today's note. Inference is not evidence.

**Only present when non-empty.** If there's nothing to carry over, omit the section entirely.

### 2. Status

A factual snapshot of the task graph and today's calendar. No recommendations.

**Contains**:

- **SEV4 cap warning** (when triggered): If more than 2 active `type: target` nodes have `goal_type: committed` and `severity: 4` (status in `{queued, ready, in_progress}`), surface a single-line concurrency-cap warning at the top of the section: `⚠ SEV4-committed concurrency cap exceeded: N active (cap = 2). Review or downgrade before adding more.` Surface only — never block. Spec: multi-parent-edges (brain PKB) §6 Q4. The on-demand counterpart is `/maintain`. See [[instructions/status-snapshot]] §3.3b.
- **Priority distribution**: ready-task counts per priority class (from `task_summary`), each shown against its **own class total** (per-class denominator, not the global ready total) so the bar reads as completion progress for that class. Compact bar chart — counts only, no narrative. Falls back to count-only when `task_summary` does not yet emit per-class totals — never fabricate or reuse the global denominator. Labels are canonical — see [Priority Labels in TAXONOMY.md](../remember/references/TAXONOMY.md#priority-labels-p0p4). See [[instructions/status-snapshot]] §3.2.
- **Deadline list**: Any task with `due` ≤ 7 days. List each as `[task-id] [[Title]] — due YYYY-MM-DD (Nd away / overdue Nd)`. Do not categorise or rank; sort by due date ascending.
- **High-focus surface**: Tasks with status: queued, ready, or in_progress, ranked by composite `focus_score`. Split into **Target-propagated urgency (SEV3+)** (tasks with `urgency >= 100` AND at least one `goals` entry linking to a target with `severity >= 3`) and **Other high-focus work** buckets. Includes inline badges `[→[[Target Title]]]` for qualifying tasks. Factual surfacing of what the graph computes — not a recommendation. Omitted when the PKB does not yet emit `focus_score`. See [[instructions/status-snapshot]] §3.3a.
- **Calendar**: Today's events from the calendar source, in time order. No commentary.
- **Pending decisions**: Count of `ready` + `review` tasks assigned to the user (one line).

**No recommendations**: Do not suggest a sequence. Do not add rationales like "start with X because Y".

> See [[instructions/status-snapshot]] for task data loading.

### 3. What Needs Attention (Inbox + Captures + Outstanding Workflows)

Email triage, mobile captures, and outstanding workflow signals, presented so the user doesn't have to open individual emails or check GitHub.

**Contains**:

- **Inbox items** grouped by conversation, with enough content that the user doesn't need to open the email. Each item ends with a `- [ ] acknowledged` checkbox so the user can mark it read. Include who wrote, what they said, what (if anything) is being asked, and any stated deadline — _factually_. Do not add editorial framing like "time-sensitive" or "ball in your court" unless it's a direct quote from the sender.
- **Mobile captures** triaged from `notes/mobile-captures/`
- Each actionable item has a task created immediately (not batched to later)
- **Outstanding workflows** — open PRs across tracked repos, bucketed by state (see below)

**Proportional detail is fine; editorial ranking is not.** Full email content for threads involving real people; one-line summary for automated notifications. That's proportional reporting. Adding "this is the most important thing today" is editorial — don't.

**Bidirectional contract**: If the user adds notes or annotations below any item, those are preserved on subsequent runs. The agent regenerates its content above user annotations but never deletes below them.

> See [[instructions/briefing-and-triage]] for email triage, sent-mail cross-referencing, and task creation.

#### Outstanding Workflows subsection

A snapshot of open PRs across tracked repos. This is the **sole place** open PRs appear in the note — the Work Log does not duplicate them.

**Bucketing** (factual state, not priority):

1. **Ready to merge** — mergeable + approved + CI passing. Rendered as `- [ ]` checkboxes with direct URL.
2. **Needs review** — mergeable, awaiting human review.
3. **Needs fixes** — conflicting, CI failing, or changes requested. Name the specific blocker.
4. **Stale** — open >7 days with no activity.
5. **Draft / autonomous** — draft PRs or polecat-worker PRs. Collapse into a count line.

Include direct PR URLs. Do not rank buckets or say "tackle X first".

**Repo list**: Use the project registry from `$AOPS_SESSIONS/polecat.yaml`. Configurable — repos are added/removed by editing the sessions-repo registry.

**Artefact dependency**: This subsection AND the Task Sweep below both consume `$AOPS_SESSIONS/state/pr-state.json`, produced by `repo-sync-cron`. `/daily` does not re-run `gh pr list` itself. If the artefact is older than **24 hours** (or missing), the subsection reports "stale" with a one-line note pointing the user to `scripts/repo-sync-cron.sh` to refresh — see [[instructions/workflow-monitor]] §"Step 6.2: Read PR State From repo-sync-cron Artefact" for the exact rendering rules.

> See [[instructions/workflow-monitor]] for the full procedure.

**PR Triage Dashboard**: When the total open-PR count across tracked repos is **≥ 10**, the skill must also render a **PR Triage Dashboard** subsection as a sibling to Outstanding Workflows. See [[instructions/pr-triage-dashboard]] for the cluster dispatch procedure.

### 4. Today's Log

Narrative of the day's work. The shape and depth depend on **when** `/daily` runs relative to the work day:

- **In-flight day (Morning Timeline mode)** — the work date has interactive sessions but no end-of-day reflection yet. Render a **chronological timeline anchored on the user's verbatim prompts**, one outcome line each, closing with a 1–2 sentence "what you were trying to do" synthesis that names the through-line and any blocker that ate time. The reader is the user returning to their desk after a context switch and wanting to remember what they were just doing. See [[instructions/morning-timeline]].
- **Closed day (Work Summary mode)** — end-of-day reflection has fired (a `## Framework Reflection` block exists in the note, or the user invoked `/end-session` / `/dump`). Render the **editorial synthesis**: a brief narrative of the shape of the day, threads that moved or stalled, patterns across sessions, with proportional detail. See [[instructions/work-summary]].
- **Empty-morning (omit)** — no interactive sessions for the work date yet. Omit `## Today's Log` entirely.

Mode selection happens automatically — see the decision matrix in [[instructions/morning-timeline]] §"When to render".

**What this section IS NOT**, in either mode:

- A prioritisation of what to do next — that belongs in §Status and the user's own `### My priorities`.
- A row-for-row rendering of session summaries — the collapsed Work Log carries only provenance (merged PRs, completed tasks), and even there we do not duplicate this narrative.
- A verdict on the day ("research day", "infrastructure day", "productive morning", "wasted hours") framed as praise or criticism — you can describe what happened in those terms factually; you cannot weight one category over another.

**The agent is trusted to choose what to surface and how within the chosen mode.** Morning Timeline mode is strictly chronological and verbatim-quote-anchored — chronology IS the structure. Work Summary mode has no prescribed sub-structure; pick the form that fits the day.

### 5. Work Log

Provenance only. A reference section for traceability — **merged PRs and completed tasks**. No Session Log table: session narration lives in Today's Log as editorial synthesis, not here as a row dump.

**Rendering**: Keep the `## Work Log` H2 heading at the top, then wrap the body in `<details><summary>(collapsed — expand for merged PRs and completed tasks)</summary> … </details>`.

**Contains** (when data is available):

- Merged PRs across tracked repos (table)
- Completed tasks (checklist with task IDs)

Open PRs are **not** duplicated here — they live in `## What Needs Attention / Outstanding Workflows`. Session summaries are **not** duplicated here — they live in `## Today's Log`.

> See [[instructions/progress-sync]] for session loading, PR querying, and task matching.

## Section Ownership and Bidirectional Sync

The daily note is a shared document between the agent and the user:

| Content type                                                                 | Rule                                                                                                                                                                        |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Machine-generated sections** (Status dashboard, Work Log tables, PR lists) | Fully replaced on each run.                                                                                                                                                 |
| **Mixed sections** (inbox items)                                             | Agent regenerates its content but preserves anything the user has written below it.                                                                                         |
| **User sections** (`### My priorities`, any section the user adds)           | Never touched by the agent.                                                                                                                                                 |
| **User ticks on agent checkboxes**                                           | Preserved. When regenerating, read the existing note first, match items by task ID / PR number / item identity, and carry the user's `[x]` state into the regenerated line. |
| **User annotations anywhere**                                                | If the user adds a note, comment, or annotation to any section, the agent preserves it.                                                                                     |

**Template markers**: Do not leave visible template artifacts (`<!-- user notes -->`, placeholder text, empty tables). If a section has no content, either omit it or write a brief natural-language empty state ("No sessions today").

## Formatting Rules

1. **No horizontal lines**: Never use `---` as section dividers (only in frontmatter)
2. **Wikilink all names**: Person names, project names, and task titles use `[[wikilink]]` syntax
3. **Task IDs**: Always include task IDs when referencing tasks (e.g., `[ns-abc] Task title`)
4. **No editorial adjectives**: Avoid words like "critical", "time-sensitive", "ball in your court", "unmissable", "the real story". State facts. The user will draw their own conclusions.

## Pipeline

The skill gathers information from multiple sources and composes the note. Independent steps run concurrently.

0. **Read existing note for the work date FIRST** — before regenerating any agenda section (Carryover, Status deadline list, What Needs Attention), parse the on-disk note (if it exists), extract user completion signals, and cache the content for subsequent steps to avoid redundant I/O:

   - **Ticked checkboxes** (`- [x]`) anywhere in the note. Capture the item identifier on that line: task ID (`[task-xxx]` or `[ns-xxx]`), PR number (`#NNN`), or — when no structured ID exists — the inline subject keyword (e.g. an email subject, PR title fragment). Use whole-word matching for keywords to avoid false positives.
   - **Inline completion annotations** the user has typed beside an item: `done`, `~~done~~`, `(done)`, `[done]`, `✓`, `resolved`, `replied`, or strikethrough (`~~…~~`) wrapping the line.
   - Build a `completed_identifiers` set from those signals before any regeneration begins.

   **Apply the set during regeneration:** for every candidate Carryover, deadline, inbox, capture, or workflow item, check whether its identifier (task ID, PR number, or normalised subject keyword) is in `completed_identifiers`. If it is:

   - **Exclude it** from sections that list only active items (Carryover, What Needs Attention, deadline lists), OR
   - Render it once with strikethrough (`~~…~~`) and the existing `[x]` preserved in sections that serve as a historical record — never strip the tick, never re-elevate as still-pending, never re-promote to "overdue".

   This is how the "Section Ownership and Bidirectional Sync" rule (§ above) is honoured in practice: a tick is a user edit, even on agent-emitted content. Re-elevating ticked items as still-pending is a correctness bug, not a styling choice.

   **Failure case to guard against** (GH #690): two OSB-vote tasks ticked done in yesterday's Carryover were re-elevated as overdue because regeneration read PKB+email but ignored the existing note. The fix is exactly this step: read the note, parse ticks, suppress.

1. **Create or open** the note (verify carryover tasks against live PKB state, intersected with the `completed_identifiers` set from step 0)

**Steps 2–3 — run in parallel** (independent):

2. **Invoke `/email`** to triage inbox (creates tasks with full context; returns inbox items for the note)
3. **Sweep mobile captures** — scan `$ACA_DATA/notes/mobile-captures/`, route each unprocessed capture to `/q` (task) or `/remember` (knowledge), delete the original, summarise in the note. See [[instructions/mobile-capture-triage]].

**Steps 4–6 — run in parallel** (independent; each reads from different data sources):

4. **Build Status** — load task summary, deadline list, calendar. See [[instructions/status-snapshot]].
5. **Sync progress + render Today's Log** — session JSONs, merged PRs, task completions → Work Log; then render `## Today's Log` in the appropriate mode:
   - In-flight day with interactive sessions → **Morning Timeline** (verbatim-prompt-anchored chronology). See [[instructions/morning-timeline]].
   - End-of-day reflection already fired → **Work Summary** (editorial synthesis). See [[instructions/work-summary]].
   - Empty morning → omit the section.
     See [[instructions/progress-sync]] for session JSON loading shared by both modes.
6. **Monitor workflows** — surface outstanding PRs in "What Needs Attention". See [[instructions/workflow-monitor]].
   - If open PRs ≥ 10, also render the PR Triage Dashboard via subagent dispatch. See [[instructions/pr-triage-dashboard]].

7. **Task completion sweep** — close tasks whose completion is evidenced by merged PRs or sent emails (see below).
8. **Output** terminal briefing and halt.

### Task Completion Sweep

This sweep closes the loop on tasks whose completion can be inferred from external signals — merged PRs and sent emails. It covers `status="review"` and `status="merge_ready"`. The sweep does **not** redefine lifecycle states — it catches tasks where the underlying work is already done but the task status was never updated (status drift).

**Procedure:**

1. Call `list_tasks(status="review")` and `list_tasks(status="merge_ready")` to get candidate tasks.
2. **Read merge evidence from `$AOPS_SESSIONS/state/pr-state.json`** (produced by `repo-sync-cron`). The artefact already contains, per tracked repo, recent merged-PR records (number, title, url, mergedAt, headRefName, body excerpt, matched task ID). Use deterministic signals as a cheap pre-filter to generate candidates — not as the decision:
   - Inspect each task's `evidence`, `notes`, `description`, and frontmatter for a linked PR number, PR URL (`pr_url`), task ID, task title, and any linked branch name
   - For each task, look up the artefact's merged-PR records: candidate PRs are those where the PR number is already linked on the task, `pr_url` matches, task ID appears in the PR body, `headRefName` matches the task's branch, or the PR title resembles the task title — these signals identify _candidates_, not confirmed matches
   - **Do NOT run `gh pr list` from this skill.** The `repo-sync-cron` artefact is the single source. If the artefact is older than 24 hours or missing, report counts as `unknown — repo-sync-cron artefact stale` and skip auto-close.
   - Only if a specific candidate PR number is already known and the artefact lacks detail, use `gh pr view <number> --json state,url,mergedAt,headRefName` as a one-off lookup (not a list scan).
     2a. **Confirm candidates via agent judgment**: For each candidate PR–task pair identified in step 2, invoke an agent against the full PR body and task body (title, description, acceptance criteria) to confirm the PR genuinely completes the task. The deterministic signals in step 2 are a pre-filter; this agent assessment is the decision. Only agent-confirmed candidates proceed to auto-close.
3. **Auto-complete clear cases**: If the agent assessment in step 2a confirms a merged PR completes a task, call `mcp__pkb__complete_task` with a completion note including the PR URL and merge timestamp as evidence.
4. **Sent-email evidence**: For tasks where the completion signal is a sent email, use correspondent and approximate subject as a pre-filter to identify candidates, then invoke an agent against the email content and task body to confirm the email represents task completion. Only auto-close when the agent assessment is unambiguous.
5. **Ambiguous cases**: When evidence exists but is ambiguous (partial subject match, PR closed but not merged), surface the task in the note under "Needs your call" within "What Needs Attention". Include the PR/email link. **Never auto-close ambiguous cases.**
6. **Stale tasks**:
   - **Weekly Triage (>14d)**: If a task has been in `review` or `merge_ready` for more than 14 days with no evidence found, surface it weekly in the note under "Stale review/merge_ready" in Status with the prompt: `Still relevant? [unblock / archive / surface]`.
   - **Auto-archive (>30d)**: If a task has been in `review` or `merge_ready` for more than 30 days with zero updates (no status change, no tags added, no notes appended since entering that status), auto-archive it. Call `mcp__pkb__complete_task` with a note explaining the auto-archive (e.g., "Auto-archived: stale >30d in review/merge_ready with no updates") and add the tag `auto-archived: stale`. Do not surface these in the note as needing review, just log the auto-archive in the sweep summary.
7. **Report summary**: Include a brief sweep summary in the Work Log section:
   - `N tasks auto-closed from merged PRs`
   - `N tasks auto-closed from sent emails`
   - `N flagged as ambiguous`
   - `N flagged as stale (>14d)` — list task IDs inline with 'Still relevant?' prompt
   - `N auto-archived as stale (>30d)`

**What counts as evidence**: An agent-confirmed merged PR, where the candidate was identified by one or more deterministic signals (PR number linked on the task, `pr_url` in frontmatter, task ID in PR body, `headRefName` matching branch, or PR title similar to task title). For email: an agent-confirmed sent reply where the candidate was identified by correspondent and approximate subject. A closed-but-not-merged PR is **not** evidence.

### Red-CI / stuck-PR loop-closer

This is the next-day backstop for the autonomous trust gate's red-CI posture (spec [[note-36c15a69]] → Modes → Autonomous → Trust gate; and `/aops-core:program` → Trust gate sub-property 4). The posture is: **a red-CI PR is first the GHA merge pipeline's job to self-heal; if it cannot, the loop must not let the PR silently stall — it converts the stuck PR into an enqueued, owned follow-up fix-task.** Never route around the failure; never merge despite red.

The Task Completion Sweep above closes tasks whose work is _done_ (merged PRs). This loop-closer handles the opposite case: PRs whose work is _stuck red_ and going nowhere on their own. The two are complementary halves of "close the loop on every open PR".

**Procedure** (runs after the Task Completion Sweep, reading the same `$AOPS_SESSIONS/state/pr-state.json` artefact — no fresh `gh pr list`):

1. From the artefact's open-PR records, select **stuck-red candidates**: PRs with at least one `statusCheckRollup` entry where `conclusion == "FAILURE"`, AND whose `updatedAt` timestamp is more than **24h** ago. A PR that is red but has a recent `updatedAt` (a fix commit or status push arrived in the last 24h) is _self-healing in progress_ — skip it; the pipeline still owns it.
2. For each stuck-red candidate, check whether a follow-up fix-task already exists (search `task_search` / scan the PR's linked tasks for an open `ci-fix` / `stuck-red` tagged task referencing this PR). If one exists and is still open, **do not duplicate** — leave it.
3. Where no open follow-up exists, **file one** via `create_task`:
   - `title`: `Fix red CI on PR #<N> — <repo>` (plain English; no raw rollup dump).
   - `body`: the PR URL, the failing check name(s) from the artefact, the head SHA, and the originating task/epic if linked. State that the GHA self-heal did not clear it within 24h.
   - `status`: `queued` only if the originating work was already human-approved for this repo; otherwise `ready` (so the human-gated `ready` → `queued` dispatch boundary is preserved, same as the rest of the framework).
   - `tags`: include `ci-fix` and `stuck-red` so step 2 can dedupe on the next run.
   - Parent it under the PR's originating epic where one is linked; otherwise file standalone in the repo's project.
4. **Severity guard at the write boundary** (retro thread 8 / #1453 — issue-sweep inflated 100% of filed tasks): a stuck-red follow-up is a routine fix, not an emergency. File at the severity the _originating_ work carried, or default low; do not auto-inflate to SEV3/4 just because CI is red.
5. **Never merge or close the red PR from this skill, and never disable/skip the failing check** (A8 — a failing check is a bug to fix, not a category to route around). The loop-closer's only job is to convert silence into an owned, queued fix-task.
6. **Report** in the Work Log sweep summary: `N stuck-red PRs → follow-up fix-tasks filed`, `N already had open follow-ups (skipped)`, `N self-healing in progress (skipped)`. If `pr-state.json` is stale (>24h) or missing, report `stuck-red loop-closer: skipped — repo-sync-cron artefact stale` and take no action (same artefact-freshness rule as the rest of `/daily`).

**Dependency note (surfaced, not assumed):** this loop-closer is the _backstop_ half of the red-CI posture. The _first-line_ half — the GHA merge pipeline actively self-healing a CI failure before this next-day pass runs — is a separate capability owned by the merge pipeline, not by `/daily`. If that GHA self-heal is not yet wired, the posture degrades gracefully (every stuck-red PR still becomes an owned fix-task here), but the "pipeline fixes it first" promise is not fully real until the GHA side exists. That is a flagged gap, not something this skill fabricates.

> Detailed procedures for each step are in the `instructions/` subdirectory.

## Error Handling

When a data source is unavailable, skip gracefully and continue. Note the gap in natural language ("Email unavailable today"), not with error codes or empty table structures. The note should always be useful even when incomplete.

## Relationship to Other Skills

- **`/pull`**: Starts execution. The daily note reports; `/pull` acts.
- **`/program`**: The autonomous program/portfolio loop relies on this skill's [Red-CI / stuck-PR loop-closer](#red-ci--stuck-pr-loop-closer) as the next-day backstop for its trust-gate red-CI posture. The daily note reports and backstops; `/program` drives the release.
- **Sleep cycle** (when implemented): Consolidates raw episodes into retrievable stores. The daily note should prefer reading consolidated state over re-processing raw sources.

## Daily Note Template (SSoT)

See [[references/note-template]] for the structural template.
