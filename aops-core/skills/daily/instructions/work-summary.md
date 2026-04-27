# Daily Note: Today's Log

## 5. Today's Log

After progress sync, generate an **editorial synthesis** of the day's work for the `## Today's Log` section. This is the key retrospective the user sees in the daily note and in the terminal. Not a log, not a table — a 100x summary from a smart editor, where every sentence teaches the reader something they couldn't pick up by skimming session data.

### Work date vs. calendar date

The target note for every write in this section is the daily note for the **work date** — the date whose work is being summarised — **not** today's calendar date. A summary written at 01:30 on 2026-04-23 about 2026-04-22's work must land in `20260422-daily.md`.

Resolve the work date in this order:

1. If the user explicitly names a date, use that.
2. Otherwise, default to **today's calendar date** (`date +%Y-%m-%d`). Today's note is for today's work; the empty-morning rule handles the case where no work has happened yet.
3. Only resolve to a _different_ date when (a) you are explicitly running a backfill / reflect pass, or (b) the user has said so. Never silently default to "the most recent date with session activity" — that flips the target whenever today's morning is quiet, and produces day-of-week errors and yesterday-content-in-today's-note.
4. If the resolved work date differs from today's calendar date, confirm once with the user (AskUserQuestion: "Summarise work for YYYY-MM-DD?") before writing.

Every reference to "the daily note" below means the work-date note. The day-of-week label in the note title and any "today / tomorrow / Nd" phrases are anchored to the **note's calendar date**, not to today's calendar date — derive them from the date in the filename via `date -d "YYYY-MM-DD" +%A`.

### Step 5.1: Gather Inputs

Collect from the sections already populated:

- **Sessions** (from Step 4.2): projects touched, prompt counts, summaries
- **Merged PRs** (from Step 4.2.5): titles and URLs
- **Completed tasks** (from Step 4.1.5): tasks closed today
- **Abandoned / unfinished threads** (from Step 4.1): work started but not completed

### Step 5.2: Identify Intra-day Changes

Read the existing `## Today's Log` section. Compare it with the newly gathered inputs. On repeat runs, report what has changed since the last `/daily` run:

- New projects touched
- New merged PRs since last update
- Threads that progressed or stalled

### Step 5.3: Write the Today's Log

Write an editorial synthesis of the day's work to the `## Today's Log` section. This replaces (not appends to) the existing content.

**Empty-log suppression**: If no sessions have occurred on the work date yet, omit `## Today's Log` entirely. If there is no content to write, skip the rest of this step and Step 5.3.1, and proceed to Step 5.4.

**Role**: You are a smart chief of staff writing a briefing for someone who was in the chair but wants the shape of the day in one read. Not an auditor reconstructing a timesheet. Not a transcript compressor. An editor who has read every session summary and has opinions about which ones mattered.

**What a great summary reads like**:

- **Insight per sentence.** Every line should teach the reader something they couldn't pick up by skimming a session table.
- **Proportional detail.** A five-hour autonomous run that closed a framework bug gets a paragraph. Nine polecat dispatches that produced one merged PR get a clause. A `/model` check or a `/clear` with no follow-up gets no words at all — it's noise.
- **Named patterns.** Name what's happening across sessions and across days. "Second unverified-carryover bug filed this week — the tooling is catching up to a class of errors." "Research plate untouched for the fourth day running." "Same mem dashboard thread you were on Tuesday, now blocked on the same schema question." These are the lines that make the summary worth reading.
- **Honest about silences.** Name what got dropped, what stalled, what you meant to do and didn't. Don't soften, don't harden, don't moralise — just say it. Dropped threads surface prominently (early in the narrative or in a short "Threads left open" stanza), not buried at the bottom — readers who are context-switching or returning after an interruption recover faster when the dropped item is the first thing they see.
- **Concrete, not abstract.** Use actual prompt text, actual PR titles, actual task IDs. "Debugged PKB search for the Afifa interview transcript question" beats "PKB lookup work." The `description` field from `user_prompt` timeline events is ground truth — prefer it over agent-generated `summary` fields.
- **Punchy verbs, past tense.** "Merged", "Debugged", "Filed", "Closed" — not "Successfully completed" or "Attempted to".
- **One shape per day.** You are describing _this_ day, not all days. Pick the form that fits — chronological, by-project, by-thread, by-significance of outcome — and commit. Don't default to the same structure every time. If you're tempted to reach for the Interactive / Dispatched / Autonomous grouping because it's familiar, ask whether it's what this day's reader needs.

**What to cut ruthlessly**:

- **Single-prompt dispatches with no outcome.** If the dispatch produced a PR, the PR is the signal; naming the dispatch line on top is double-counting. If it produced nothing, the dispatch is noise.
- **`/clear`-only and `/model`-only sessions.** Context-switching overhead, not work.
- **Hex-hash polecat worker sessions.** Fold into a summary count ("~15 polecat workers → 20 merged PRs") rather than naming each.
- **Duplicate coverage.** If the Work Log tables already count something, don't re-count it here — describe its _meaning_, not its existence.
- **Filler connectives.** "In the afternoon you also…" / "Meanwhile…" tend to pad; cut unless they carry real information.

**What stays off-limits** (inherited from the skill's no-ranking philosophy):

- Do not rank what the user should do next. That's §Status and the user's own `### My priorities`.
- Do not declare verdicts on the day ("research day beat infrastructure day") framed as praise or criticism. You can describe what happened in those terms factually; you cannot weight one category over another.
- Do not inject urgency. "Ball in your court" / "time-sensitive" / "critical" are banned unless quoted from a source.

**Length**: Fit the day. A genuinely quiet day might be three sentences. A heavy day might be four paragraphs. Don't pad. Don't under-report just because you're trying to be terse — if there are real patterns to name, name them.

**Repeat-run update**: If this is a second run of the same day, the first sentence should name what's new since the last write, not re-summarise the full day.

**Data filters before you start**: Read session summary JSONs for the work date. Filter out auto-commit sessions (`commit-changed` in filename, or filename starts with `sessions-`) and polecat workers (project field matches a short hex hash, e.g. `^[a-f0-9]{7,8}$`). Use `timeline_events` where `type == "user_prompt"` for prompt count and content, `summary` for agent outcomes, `token_metrics.efficiency.session_duration_minutes` for duration, and `project` for context.

**Worked example — good vs. bad**:

_Bad_ (the anti-pattern — rows, noise, no synthesis):

> **Dispatched** (1 user prompt):
>
> - **crew-barbara session** (07:17): Dispatched: crew-barbara session
> - **crew-barbara metro graph** (12:55): Dispatched: metro graph update
> - **brain session** (11:23): Dispatched: brain session
>
> **Autonomous** (0 user prompts):
>
> - **brain-j5hw6l4kt6** (308 min): Filed academicOps #714

_Good_ (the target — synthesis, proportion, pattern):

> A five-hour autonomous brain run closed a self-inflicted daily-note bug overnight — [#714] documents the unverified-carryover failure mode. It's the second bug in that family this week, and the tooling is visibly catching up. The rest of the day was conductor work: short dispatches to polecat workers that landed three more merged PRs on the mem dashboard thread. HSSC manuscript review didn't get touched — fourth day in that state. Tomorrow's Jacob meeting prep is still open.

### Step 5.3.1: Update daily note frontmatter

After writing Today's Log, update the same note's frontmatter fields. This is the sole write point for the daily narrative.

1. Adapt Today's Log from prose into 3-5 bullets:
   - Second person ("you merged...", "you debugged...")
   - Each bullet under 80 characters
   - Cover: what happened, what's still open, and any pattern worth naming
   - Shape the bullets the way the narrative is shaped — if the narrative led with a dropped thread, the bullets should too. Do not impose a forward prioritisation of what the user should do next.
2. Read the work-date note file
3. Update the YAML frontmatter fields:
   - `daily_narrative`: the prose summary (excluding "Threads left open" stanza if separated)
   - `daily_story`: the bullet array from step 1
   - `narrative_generated`: ISO 8601 timestamp
4. Write the file back

### Step 5.4: Terminal Briefing Output

After updating the daily note, output a concise briefing to the terminal:

```
## Daily Note (vN)

[Today's Log text from 5.3]

**Since last update**: [Summary of changes since last run]
**Threads open**: [Titles of unfinished threads]

**Totals**: N PRs merged, N tasks completed.

Daily note updated at [path].
Use `/pull` to resume work.
```
