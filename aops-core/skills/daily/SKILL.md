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
version: 4.0.0
permalink: skills-daily
---

# Daily Note Skill

Compose and maintain a daily note that **reports** the state of the day to the user. The note is a factual briefing — what's in the inbox, what's on the calendar, what's due, what's open, what ran. It does **not** curate, rank, recommend, or suggest sequences.

Location: `$ACA_DATA/daily/YYYYMMDD-daily.md`

**Work date ≠ calendar date.** End-of-day summaries and reflections target the **work-date** note — the note for the day being described — not today's note. A reflection written at 01:30 on 2026-04-23 about 2026-04-22's work lands in `20260422-daily.md`. See [[instructions/reflect]] Step 0 and [[instructions/work-summary]] §"Work date vs. calendar date".

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

Items carrying forward from yesterday (verified against live task state — never copy blindly from yesterday's note) and end-of-day abandoned todos. Each item is a checkbox (`- [ ] [task-id] Title`) so the user can tick it off.

**Only present when non-empty.** If there's nothing to carry over, omit the section entirely.

### 2. Status

A factual snapshot of the task graph and today's calendar. No recommendations.

**Contains**:

- **Priority distribution**: P0/P1/P2/P3 counts of ready tasks (from `task_summary`). Presented as a compact bar chart — counts only, no narrative.
- **Deadline list**: Any task with `due` ≤ 7 days. List each as `[task-id] [[Title]] — due YYYY-MM-DD (Nd away / overdue Nd)`. Do not categorise or rank; sort by due date ascending.
- **Calendar**: Today's events from the calendar source, in time order. No commentary.
- **Pending decisions**: Count of `ready` + `review` tasks assigned to the user (one line).

**No recommendations**: Do not emit SHOULD/DEEP/ENJOY/QUICK/UNBLOCK categories. Do not suggest a sequence. Do not add rationales like "start with X because Y".

**`### My priorities` subsection**: A user-owned space. The agent creates the empty heading on first run and never writes to it afterwards. Do not ask the user what their priorities are — they will write them in if and when they want to.

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

**Graceful degradation**: If `gh` CLI is unavailable or authentication fails, note the gap in natural language ("GitHub CLI unavailable — skipped workflow monitoring") and continue. Never error or produce empty table structures.

**Repo list**: Use the project registry from `$POLECAT_HOME/polecat.yaml`. Configurable — repos are added/removed by editing polecat.yaml.

> See [[instructions/workflow-monitor]] for the full procedure.

### 4. Today's Log

An editorial synthesis of the day's work. Not a transcript, not an audit log, not a table of sessions — the 100x summary a skilled chief of staff would write for someone who was in the chair but wants the shape of the day in one read.

**Empty-morning rule**: If the work date has no sessions yet (typical morning run), omit this section entirely.

**What this section IS**: A brief narrative that captures the shape of the day. Which threads moved. Which stalled. Which dropped. What the autonomous runs produced. Patterns across sessions or across days. Real work disproportionately named; noise folded into clauses or omitted entirely.

**What this section IS NOT**:

- A prioritisation of what to do next — that belongs in §Status and the user's own `### My priorities`.
- A row-for-row rendering of session summaries — the collapsed Work Log carries only provenance (merged PRs, completed tasks), and even there we do not duplicate this narrative.
- A verdict on the day ("research day", "infrastructure day") framed as praise or criticism — you can describe what happened in those terms factually; you cannot weight one category over another.

**The agent is trusted to choose what to surface and how.** No prescribed sub-structure (no required "Interactive / Dispatched / Autonomous" blocks, no enforced chronology). Pick the form that fits this day — by thread, by project, by significance of outcome, chronologically — and commit. See [[instructions/work-summary]] for the full editorial brief.

### 5. Work Log (collapsed by default)

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

1. **Create or open** the note (verify carryover tasks against live PKB state)

**Steps 2–3 — run in parallel** (independent):

2. **Invoke `/email`** to triage inbox (creates tasks with full context; returns inbox items for the note)
3. **Sweep mobile captures** — scan `$ACA_DATA/notes/mobile-captures/`, route each unprocessed capture to `/q` (task) or `/remember` (knowledge), delete the original, summarise in the note. See [[instructions/mobile-capture-triage]].

**Steps 4–6 — run in parallel** (independent; each reads from different data sources):

4. **Build Status** — load task summary, deadline list, calendar. See [[instructions/status-snapshot]].
5. **Sync progress** — session JSONs, merged PRs, task completions → Work Log + Today's Log. See [[instructions/progress-sync]].
6. **Monitor workflows** — surface outstanding PRs in "What Needs Attention". See [[instructions/workflow-monitor]].

7. **Task completion sweep** — close tasks whose completion is evidenced by merged PRs or sent emails (see below).
8. **Output** terminal briefing and halt.

### Task Completion Sweep

This sweep closes the loop on tasks whose completion can be inferred from external signals — merged PRs and sent emails. It covers `status="review"` and `status="merge_ready"`. The sweep does **not** redefine lifecycle states — it catches tasks where the underlying work is already done but the task status was never updated (status drift).

**Procedure:**

1. Call `list_tasks(status="review")` and `list_tasks(status="merge_ready")` to get candidate tasks.
2. Group tasks by repository, then check for merge evidence repo-by-repo:
   - Inspect each task's `evidence`, `notes`, `description`, and frontmatter for a linked PR number, PR URL (`pr_url`), task ID, task title, and any linked branch name
   - For each repo, fetch merged PRs once with `gh pr list --state merged --json number,title,url,mergedAt,body,headRefName`
   - Match tasks locally against the fetched PR set: PR number already linked on the task, `pr_url` in frontmatter, task ID in PR body, `headRefName` matching the task's linked branch, or PR title matching the task title (whole-word boundaries)
   - Only if a specific candidate PR number is already known and the batch result lacks needed detail, use `gh pr view <number> --json state,url,mergedAt,headRefName`
3. **Auto-complete clear cases**: If a merged PR is found matching the task, call `mcp__pkb__complete_task` with a completion note including the PR URL and merge timestamp as evidence. No human confirmation needed — the merge is sufficient evidence.
4. **Sent-email evidence**: For tasks where the completion signal is a sent email, cross-reference against recent sent items. If a sent reply matches the task's correspondent + subject (whole-word boundaries) within 48 hours of task creation, call `mcp__pkb__complete_task` with the sent email as evidence. Only auto-close when the match is unambiguous.
5. **Ambiguous cases**: When evidence exists but is ambiguous (partial subject match, PR closed but not merged), surface the task in the note under "Needs your call" within "What Needs Attention". Include the PR/email link. **Never auto-close ambiguous cases.**
6. **Stale tasks**: If a task has been in `review` or `merge_ready` for more than 14 days with no evidence found, surface it under "Stale review/merge_ready" in Status. Do not auto-close.
7. **Report summary**: Include a brief sweep summary in the Work Log section:
   - `N tasks auto-closed from merged PRs`
   - `N tasks auto-closed from sent emails`
   - `N flagged as ambiguous`
   - `N flagged as stale (>14d)` — list task IDs inline

**What counts as evidence**: A merged PR linked by `pr_url`, PR number already on task, task ID in PR body, `headRefName` matching branch, or PR title matching task title (whole-word boundaries). A sent email matching correspondent + subject (whole-word boundaries) within 48 hours of task creation. A closed-but-not-merged PR is **not** evidence.

> Detailed procedures for each step are in the `instructions/` subdirectory.

## Error Handling

When a data source is unavailable, skip gracefully and continue. Note the gap in natural language ("Email unavailable today"), not with error codes or empty table structures. The note should always be useful even when incomplete.

## Relationship to Other Skills

- **`/pull`**: Starts execution. The daily note reports; `/pull` acts.
- **Sleep cycle** (when implemented): Consolidates raw episodes into retrievable stores. The daily note should prefer reading consolidated state over re-processing raw sources.

## Daily Note Template (SSoT)

See [[references/note-template]] for the structural template.
