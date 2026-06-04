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

# Daily Note Guidelines

Compose and maintain the daily note at `$ACA_DATA/daily/YYYYMMDD-daily.md`. The note serves as a factual, non-judgmental report of the day's state (deadlines, inbox, open threads, calendar, session logs). Do not suggest task prioritization, sequences, or ratings.

## Core Directives

1. **Date Anchor**: Base the note filename and relative date phrases strictly on today's calendar date (`date +%Y-%m-%d`).
2. **Work Date vs. Calendar Date**: Narrative summaries or reflections written after midnight about yesterday's work must land in the note for yesterday's date, not today's.
3. **Empty Morning Rule**: If today has no session activity yet, omit the narrative log entirely; do not backfill yesterday's narrative into today's note.
4. **Bidirectional Sync**: Preserve user annotations, comments, and ticked states (`[x]`) on regenerated items. Match existing items by ID/PR/subject keyword and carry user ticks forward.
5. **Tool Loading & Degraded Sources**:
   - Explicitly load deferred tools (e.g. `mcp__outlook__*`) before querying email/calendar. Retry once with canonical names on transient tool-not-found errors.
   - If a source genuinely fails after attempting to load and retry, list it in a single line under the lede (**Degraded sources:**) and collapse the corresponding section. Do not render empty sections with bare footnotes.

## Daily Note Structure

The daily note must follow this exact section order:

1. **Lede (Shape of Right Now)**: A 2–3 line, present-tense synthesis of the day's story and through-line. Persist to the `daily_narrative` frontmatter field.
2. **Today's Log (Recovery Substrate)**:
   - **In-flight**: A chronological Morning Timeline anchored on verbatim user prompts with outcome summaries. Add "Needs your call" pending decision counts.
   - **Closed**: Factual editorial summary of progress, patterns, and blockers.
   - **Empty Morning**: Omit section entirely.
3. **Status**: Factual snapshot. Includes SEV4 committed targets cap warning (warn if >2), ready tasks counts by priority denominator, deadlines (due ≤7 days sorted ascending), high-focus tasks sorted by `focus_score`, and calendar events. No recommendations.
4. **What Needs Attention**:
   - **Inbox items** with conversation content summaries and checkboxes.
   - **Mobile captures** scanned and routed to tasks/memories.
   - **Outstanding Workflows**: PR status snapshot (merged, review, fixes, stale, drafts) sourced from the `pr-state.json` artifact (flag as stale if artifact >24h old). PR Triage Dashboard if PRs ≥10.
5. **Carryover**: Uncompleted tasks from yesterday (verified against live PKB state). Omit if empty.
6. **Work Log**: Provenance data wrapped in a `<details>` collapsible tag, listing merged PRs and completed tasks. No session narrative duplication.

## Loop-Closer Sweeps

### 1. Task Completion Sweep

Close review/merge_ready tasks where completion is evidenced by merged PRs or sent emails in `pr-state.json`.

- **Match Verification**: Use an agent to confirm correspondence between tasks and PR/email content. Enforce AC verification before completing.
- **Auto-archive**: Weekly triage tasks stale >14d (add 'Still relevant?' prompt). Auto-complete clear cases. Auto-archive tasks stale >30d with tag `auto-archived: stale`.
- **Partial Work**: Draft PRs / tasks with `status: partial` are not sweep targets; do not auto-close or flag as stalled.

### 2. Red-CI / Stuck-PR Loop-Closer

Convert stalled, failing CI PRs into owned fix-tasks.

- Identify PRs with failing checks (`FAILURE` conclusion) updated >24h ago.
- If no fix-task exists, create a task (title `Fix red CI on PR #<N>`, parented under the epic/project) with the original severity. Do not merge or bypass.

## Output Expectations

- Respond with a concise update statement: "Daily note updated. Use `/pull` to start work." and halt.
