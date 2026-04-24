# Daily Note: Today's Log

## 5. Today's Log

After progress sync, generate a factual account of the day's work for the `## Today's Log` section. This is the **key retrospective** the user sees in the daily note and in the terminal. It is a log, not an editorial — report what happened, not what mattered.

### Work date vs. calendar date

The target note for every write in this section is the daily note for the **work date** — the date whose work is being summarised — **not** today's calendar date. A summary written at 01:30 on 2026-04-23 about 2026-04-22's work must land in `20260422-daily.md`.

Resolve the work date in this order:

1. If the user explicitly names a date, use that.
2. Otherwise, default to the most recent date with session activity in `$AOPS_SESSIONS/summaries/`.
3. If the resolved work date differs from today's calendar date, confirm once with the user (AskUserQuestion: "Summarise work for YYYY-MM-DD?") before writing.

Every reference to "the daily note" below means the work-date note.

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

### Step 5.3: Write the Log

Write a 2-4 sentence factual summary to the work-date note's `## Today's Log` section. This replaces (not appends to) the existing content.

**Empty-log suppression**: If no sessions have occurred on the work date yet (e.g. the morning run before any work has happened), omit the `## Today's Log` and `### Session Flow` sections entirely. If there is no content to write, skip the rest of this step and Step 5.3.1, and proceed to Step 5.4.

**Style guide**:

- **Factual, not editorial.** Report what happened. Do not rank what mattered. Do not call something "the real story" or "the main work of the day". Do not lead with a "most impactful" item — lead with what happened first, or group by project.
- **No work-type hierarchy.** Do not promote research over infrastructure (or vice versa). Do not write "Infrastructure day — no research progress" as a judgment. If the user wants a verdict on their day, they'll write one in `### My priorities`.
- **Mention specific PR numbers and task IDs** for traceability.
- **Use concrete details from user prompts, not abstract labels.** "Debugged PKB search for [[specific research question]]" tells a story. "[[Topic area]] PKB lookup" is a label. The `description` field from `user_prompt` timeline events contains the ground truth — use it.
- **Punchy verbs, past tense.** "Merged 3 PRs...", "Debugged X...", "Filed task Y..." — not "Successfully completed" or "Attempted to".
- **Group by project or by chronology, not by judgment.** Either "Worked on OSB benchmarking this morning, then mem dashboard this afternoon" (chronological) or "OSB benchmarking: ..., mem dashboard: ..., framework: ..." (by-project). Pick one and stick to it. Do not reorder to make research "lead".

**Current Momentum**: If this is a repeat run, ensure the first sentence summarizes the work done since the last update.

**Unfinished threads**: If the path reconstruction identified abandoned or interrupted work, add a bullet under the log:

- **Threads left open**: "[Task Title]" (started in session [id] but unfinished).

Do not soften or harden this — report plainly.

### Step 5.3.1: Update daily note frontmatter

After writing Today's Log, update the same note's frontmatter fields. This is the sole write point for the daily narrative.

1. Adapt Today's Log from prose into 3-5 bullets:
   - Second person ("you merged...", "you debugged...")
   - Each bullet under 80 characters
   - Cover: what happened, what's still open
   - **Order by chronology or project**, not by significance. Do not promote any category of work above another.
2. Read the work-date note file
3. Update the YAML frontmatter fields:
   - `daily_narrative`: the 2-4 sentence prose summary (excluding "Threads left open" bullet)
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
