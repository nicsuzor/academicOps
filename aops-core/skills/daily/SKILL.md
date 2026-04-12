---
name: daily
type: skill
category: instruction
description: Daily note lifecycle - briefing, task recommendations, progress sync, and work summary. SSoT for daily note structure.
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
allowed-tools: Read,Bash,Grep,Write,Edit,AskUserQuestion,Skill,~~email
owner: pauli
version: 3.0.0
permalink: skills-daily
---

# Daily Note Skill

Compose and maintain a daily note that helps the user orient, prioritise, and track their day.

Location: `$ACA_DATA/daily/YYYYMMDD-daily.md`

## Purpose

The daily note answers three questions for a knowledge worker returning to their desk:

1. **What needs my attention?** — Deadlines, emails requiring action, decisions blocking other work
2. **What should I work on?** — Curated recommendations balancing urgency, deep work, variety, and momentum
3. **What happened today?** — A narrative synthesis of the day's work, oriented around significance not completeness

The note is a _planning_ document, not an execution trigger. After the note is updated, output "Daily planning complete. Use `/pull` to start work." and HALT. User stating a priority ≠ authorization to execute it.

## Quality Criteria (P#115)

A good daily note is evaluated qualitatively, not by structural compliance:

- **Orientation in 30 seconds**: Can the user glance at the note and know what matters? The visual hierarchy should match the priority hierarchy. Deadlines and high-stakes items should be unmissable. Routine maintenance should not compete for attention.
- **Emotional calibration**: Surfaces urgency without triggering anxiety. Frames dropped threads as "pick up where you left off," not "you failed." Balances pressure with variety.
- **Proportional detail**: Major research milestones, external deadlines, and items involving other people get more space and context than internal tooling tasks. A paper deadline and a CI fix are not presented with equal weight.
- **Actions linked to tasks**: Every actionable item references its task ID. Every task mentioned in FYI has a corresponding task created or updated in the PKB. Information captured but not persisted is information lost.
- **Nothing lost**: Email items that need responses have tasks. Carryover from yesterday is verified against live task state (no phantom overdue). User annotations are preserved.

## Invocation

Every `/daily` invocation updates the note in place. The skill is designed to be run repeatedly throughout the day. There are no separate modes.

```
/daily          # Update the note (create if missing)
/daily sync     # Alias for muscle memory
```

## Note Structure

The daily note has **five sections**, each serving a distinct purpose. The agent composes these sections using its judgment about what matters most in context (P#116). The structure below defines WHAT each section achieves, not a rigid template.

### 1. Focus

The first thing the user sees. Combines priority overview and curated task recommendations in one place.

**Contains**:

- Priority distribution (P0/P1/P2/P3 counts of actionable tasks — consistent filtering in both numerator and denominator)
- Deadline alerts (any task due within 48 hours, unmissable formatting)
- ~10 curated recommendations across categories: urgent/overdue (SHOULD), strategic deep work (DEEP), variety/energy (ENJOY), quick wins (QUICK), unblocking others (UNBLOCK)
- Suggested sequence with brief rationale

**Quality guidance**: Weight recommendations by _significance to the person_, not just priority field values. An overdue email reply to a colleague is more important than a P0 framework task that has been P0 for months. A paper deadline matters more than a CI fix. The agent should understand the user's world — their research commitments, their students, their external obligations — and recommend accordingly.

**User priorities subsection**: After presenting recommendations, ask the user what sounds right for today. Record their response in a `### My priorities` subsection. This subsection is never overwritten on subsequent runs.

> See [[instructions/focus-and-recommendations]] for task data loading and recommendation reasoning.

### 2. What Needs Attention (FYI + Captures)

Email triage and mobile captures, presented as a briefing the user reads _in the note itself_ — not by opening individual emails.

**Contains**:

- Email threads grouped by conversation, with enough content that the user doesn't need to open the email
- Mobile captures triaged from `notes/mobile-captures/`
- Each actionable item has a task created immediately (not batched to later)

**Quality guidance**: FYI items involving real people (students, collaborators, funders) get full context — who said what, what's being asked, what the deadline is. Automated notifications, newsletters, and low-signal items get a single line or are omitted entirely. The agent triages by significance, not by recency.

**Bidirectional contract**: If the user adds notes or annotations below any FYI item, those are preserved on subsequent runs. The agent regenerates its content above user annotations but never deletes below them.

> See [[instructions/briefing-and-triage]] for email triage, sent-mail cross-referencing, and task creation.

### 3. Today's Story

A 2-4 sentence narrative synthesis of the day's work, followed by a structured **Session Flow** subsection. This is the _editorial_ section — the agent's judgment about what the day's work means, not a log of what happened.

**Quality guidance**: Lead with the most significant work, not the most recent. Research progress, paper milestones, and external commitments matter more than framework PRs. If 8 PRs were merged on internal tooling but no progress was made on the paper deadline, the story should note the tooling work briefly and highlight the gap. Mention specific PR numbers and task IDs for traceability, but embed them in narrative, not tables.

**Distinguish human work from agent output.** In a conductor workflow, impressive autonomous output (an agent producing 6 tasks over 4 hours) is not the same as the human doing deep work. The story should reflect what the human actually engaged with — use prompt count as the primary signal. An autonomous session that produced a lot is worth a sentence ("dispatched X, which produced Y"); an interactive session where the human debugged something for 5 minutes with 3 prompts is where the narrative focus should be. The reader wants to know: what did _I_ spend my attention on today?

If this is a repeat run during the day, emphasise what changed since the last update. Note dropped threads (work started but not finished) with gentle framing.

#### Session Flow subsection (`### Session Flow`)

Reconstructs the day's attention flow from session summary JSONs in `$AOPS_SESSIONS/summaries/`. This answers: what did I actually spend my attention on, where did I get pulled away, and what's still hanging?

**Structure**:

```markdown
### Session Flow

**Where your attention went** (interactive sessions, 2+ user prompts):

1. **[Topic]** ([time], [N prompts], [duration]): [What the user was doing — use their actual prompt text, not agent-generated summaries. What was the outcome.]
2. ...

**Dispatched work** (1-prompt sessions — fire and forget):

- **[Topic]** ([time]): [What was dispatched and what came back. Note if the agent ran autonomously for a long time.]

**Autonomous background runs** (0-prompt sessions):

- **[Session ID]** ([duration]): [What the agent produced. Flag this as zero human attention cost.]

**Threads left hanging**:

- [Topic not completed, with context on why]

**The day in a line**: [One-sentence editorial summary]
```

**The primary signal for attention cost is user prompt count**, not session duration or output complexity. Extract `timeline_events` where `type == "user_prompt"` for each session. See [[instructions/progress-sync]] Step 4.2 for the engagement classification table.

A 337-minute autonomous session with 0 prompts costs the human nothing — it's fire-and-forget. A 5-minute session with 4 prompts is where they were actively thinking. Lead with where the human's attention actually went, not where the most output was produced.

**Use the user's actual prompts as ground truth**: The `description` field in user prompt timeline events tells you what the human was trying to do. Agent-generated `summary` fields are abstractions of abstractions. When writing Session Flow entries, reference the prompt content (e.g., "debugged PKB search for [[specific topic]]" not "PKB lookup").

**Categories of attention** (derived from prompt count):

- **Deep engagement** (4+ prompts): Sustained human involvement — debugging, discussing, iterating. These are the real attention cost centers.
- **Interactive** (2–3 prompts): Back-and-forth with the agent. Moderate attention.
- **Dispatched** (1 prompt): Human kicked it off and moved on. Conductor work. Low attention cost.
- **Autonomous** (0 prompts): Agent ran without human involvement. Zero attention cost regardless of duration or output volume.
- **Frustration cost**: Sessions that should have been quick but weren't (broken deploys, failed builds, repeated attempts). The attention cost is disproportionate to the clock time. Identify these by multiple short sessions on the same topic, or sessions where prompt content shows escalating frustration.

**Work type ordering**: Within each attention category, list research/academic sessions before infrastructure sessions. If the day's only deep-engagement session was a research analysis, it should be the first item under "Where your attention went" — not buried after dispatched infrastructure work. Research work that produced no GitHub artifacts but high human engagement is the headline, not the footnote. See [[instructions/progress-sync]] for work type classification.

**What counts as a distraction vs. conductor work**: A quick check on an unrelated project is conductor work if it's a deliberate scan (1 prompt, moved on). It's a distraction if it pulls the user into reactive engagement (2+ prompts on something unplanned), or if a "quick check" turns into a 2-hour tangent. Judge by prompt count and what happened after — did the user return to their main thread, or did they drift?

**Data source**: Read session summary JSONs for the current day. Filter out auto-commit sessions (`commit-changed` in filename, or filename starts with `sessions-`) and polecat workers (project field matches a short hex hash, e.g. `^[a-f0-9]{7,8}$`). Use `timeline_events` where `type == "user_prompt"` for prompt count and content (the primary attention signal), `summary` for agent outcomes, `token_metrics.efficiency.session_duration_minutes` for duration context, and `project` for context-switch detection.

> See [[instructions/work-summary]] for story synthesis guidance.

### 4. Work Log (collapsed by default)

A reference section for traceability — what sessions ran, what PRs merged, what tasks were completed. This section exists for the record, not for the user's morning read.

**Contains** (when data is available):

- Merged PRs across tracked repos (table format)
- Open PRs needing decisions (with recommended actions)
- Session log (table of sessions with project, prompt count, and description)
- Project accomplishments (checklist items linked to tasks)

**Quality guidance**: This section should be _scannable but not prominent_. It's reference material. If GitHub CLI is unavailable or no sessions ran, the section should be minimal ("No sessions today") rather than filled with empty tables and "n/a" markers.

**Session log entries must be meaningful the next morning.** For sessions with user prompts, use the first user prompt's `description` (truncated) as the session description, not the agent-generated `summary`. For 0-prompt (autonomous) sessions, base the description on what the agent produced — e.g., `autonomous: summarized AXIOMS.md for daily skill update`. "Pulled task-7275a7b8" is useless — what was the task about? "Reviewed swarm-supervisor skill update" — what was the update? Include enough context that someone reading the log tomorrow can reconstruct what happened without opening the session JSON. Include the prompt count (e.g., "2p" or "0p") so the reader can distinguish interactive work from autonomous runs at a glance.

Accomplishments should be linked to their corresponding tasks. Every `[x]` item should reference a task ID where possible.

> See [[instructions/progress-sync]] for session loading, PR querying, and task matching.

### 5. Carryover + Abandoned

Items carrying forward from yesterday (verified against live task state — never copy blindly from yesterday's note) and end-of-day abandoned todos.

**Only present when non-empty.** If there's nothing to carry over, omit the section entirely rather than showing empty placeholders.

## Section Ownership and Bidirectional Sync

The daily note is a _shared document_ between the agent and the user. The ownership contract:

| Content type                                                              | Rule                                                                                                                                     |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Machine-generated sections** (Work Log tables, PR lists, priority bars) | Fully replaced on each run.                                                                                                              |
| **Mixed sections** (Focus recommendations, FYI items)                     | Agent regenerates its content but preserves anything the user has written. User content is identified by position (below agent content). |
| **User sections** (My priorities, any section the user adds)              | Never touched by the agent.                                                                                                              |
| **User annotations anywhere**                                             | If the user adds a note, comment, or annotation to any section, the agent preserves it.                                                  |

**What happens when the user edits the note**: The agent should read the note before updating and notice user changes. If the user has crossed out a recommendation, added context to an FYI item, or written priorities, those are signals the agent should respect — not overwrite.

**Template markers**: Do not leave visible template artifacts (`<!-- user notes -->`, placeholder text like "(End of day carryover)", empty tables). If a section has no content, either omit it or write a brief natural-language empty state ("No sessions today"). The note should read as a composed document, not a filled-in form.

## Formatting Rules

1. **No horizontal lines**: Never use `---` as section dividers (only in frontmatter)
2. **Wikilink all names**: Person names, project names, and task titles use `[[wikilink]]` syntax
3. **Task IDs**: Always include task IDs when referencing tasks (e.g., `[ns-abc] Task title`)
4. **Proportional formatting**: Important items get more visual weight (bold, callout formatting). Routine items get less. Not everything deserves the same treatment.

## Pipeline

The skill gathers information from multiple sources and composes the note. The order below is a typical sequence, not a rigid pipeline — the agent may adjust based on what's available:

1. **Create or open** the note (verify carryover tasks against live PKB state)
2. **Invoke `/email`** to triage inbox (creates tasks with full context; returns FYI items for the daily note)
3. **Compose Focus** (load task data, reason about recommendations, engage user on priorities)
4. **Sync progress** (session JSONs, merged PRs, task completions → Work Log + Today's Story)
5. **Sweep review-status tasks** (see below)
6. **Output** terminal briefing and halt

### Review Sweep (Step 5)

`status="review"` means the task needs human/manager review — typically after a failure or blocked execution path. This sweep does **not** redefine that lifecycle state. Instead, it catches tasks that are still marked `review` even though repository evidence suggests the work may already be complete and the task status was never updated (status drift).

**Procedure:**

1. Call `list_tasks(status="review")` to get all tasks currently in review.
2. Group tasks by repository, then check for merge evidence repo-by-repo:
   - First inspect each task's `evidence`, `notes`, and `description` for a linked PR number, PR URL, task ID, task title, and any linked branch name
   - For each repo represented by those tasks, fetch merged PRs once with `gh pr list --state merged --json number,title,url,mergedAt,body,headRefName`
   - Match tasks locally against the fetched PR set: PR number already linked on the task, task ID in PR body, `headRefName` matching the task's linked branch, or PR title substring-matching the task title
   - Only if a specific candidate PR number is already known and the batch result lacks needed detail, use `gh pr view <number> --json state,url,mergedAt,headRefName` as a targeted confirmation step
3. **Auto-complete only clear status-drift cases**: If a merged PR is found and the task's remaining `review` status appears stale rather than an active human-review step, call `mcp__pkb__complete_task` with a completion note explaining the sweep reconciled an out-of-date task state and evidence including the PR URL and merge timestamp. No human confirmation needed — the merge is sufficient evidence.
4. **Flag stale tasks**: If a task has been in `review` status for more than 14 days with no merge evidence found, flag it for user triage. Do not auto-close or auto-abandon stale tasks — surface them explicitly in the Focus section with a brief summary (task ID, title, age, what was expected to close it).
5. **Report summary**: Include a brief sweep summary in the Work Log section:
   - `N tasks auto-completed from merged PRs`
   - `N tasks flagged as stale (>14d in review)` — list task IDs inline

**What counts as evidence**: A merged PR linked to the task by any of: PR number already linked on task, task ID in PR body, `headRefName` matching task's linked branch, PR title substring-matching task title. A closed-but-not-merged PR is not evidence of completion — flag it separately if found.

> Detailed procedures for each step are in the `instructions/` subdirectory. These procedures describe best practices and edge cases — they are guidance for the agent, not scripts to execute mechanically (P#116).

## Error Handling

When a data source is unavailable, skip gracefully and continue. Note the gap in natural language ("Email unavailable today"), not with error codes or empty table structures. The note should always be useful even when incomplete.

## Relationship to Other Skills

- **Briefing bundle** (`/bundle`): The daily note surfaces information; the bundle adds editorial judgment for decision-making (coversheets, email drafts, annotation targets). See [[specs/daily-briefing-bundle.md]].
- **Sleep cycle** (when implemented): Consolidates raw episodes into retrievable stores. The daily note should prefer reading consolidated state over re-processing raw sources.
- **`/pull`**: Starts execution. The daily note plans; `/pull` acts.

## Daily Note Template (SSoT)

See [[references/note-template]] for the structural template.
