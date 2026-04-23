# Daily Note: Work Summary

## 5. Work Summary

After progress sync, generate a brief natural language summary of the day's work. This is the **key output** that the user sees both in the daily note and in the terminal. When running multiple times a day, emphasize recent momentum and context shifts.

### Work date vs. calendar date

The target note for every write in this section is the daily note for the **work date** — the date whose work is being summarised — **not** today's calendar date. A summary written at 01:30 on 2026-04-23 about 2026-04-22's work must land in `20260422-daily.md`.

Resolve the work date in this order:

1. If the user explicitly names a date, use that.
2. Otherwise, default to the most recent date with session activity in `$AOPS_SESSIONS/summaries/`.
3. If the resolved 'work date' differs from today's calendar date, confirm once with the user (AskUserQuestion: "Summarise work for YYYY-MM-DD?") before writing.

Every reference to "the daily note" below means the work-date note.

### Step 5.1: Gather Inputs

Collect from the sections already populated:

- **Today's Path** (from Step 4.1): recent threads and abandoned work
- **Merged PRs** (from Step 4.2.5): titles and count
- **Session accomplishments** (from Step 4.2): what was done in each session
- **Completed tasks** (from Step 4.1.5): tasks closed today
- **Focus goals** (from `### My priorities`): what the user intended to do

### Step 5.2: Identify Intra-day Shifts

Read the existing `## Today's Story` section. Compare it with the newly gathered inputs.
Identify what has changed since the last `/daily` run:

- New projects touched
- Significant progress on a specific task
- Pivots or sidetracks (e.g., "Shifted focus to a bug fix after session X")

### Step 5.3: Generate Today's Story

Write a 2-4 sentence natural language summary to the work-date note's `## Today's Story` section. This replaces (not appends to) the existing Today's Story content.

**Empty-story suppression**: If no sessions have occurred on the 'work date' yet (e.g. the morning run before any work has happened), omit the ## Today's Story and ### Session Flow sections entirely rather than emitting empty headings or placeholder prose. If there is no content to write, skip the rest of this step and Step 5.3.1, and proceed to Step 5.4.

**Current Momentum**: If this is a repeat run, ensure the first sentence summarizes the work done **since the last update**.

**Dropped Threads**: If the path reconstruction identified "Abandoned Work", add a single bullet point under the story:

- **⚠ Dropped Threads**: "[Task Title]" (started in session [id] but unfinished).

**Style guide**:

- Write in past tense, first person plural or third person ("Merged 3 PRs..." / "The day focused on...")
- Lead with the most impactful work, not chronological order
- Mention specific PR numbers and task IDs for traceability
- If goals were set in Focus, note alignment or drift briefly
- **Punchy Verbs**: Avoid robotic preambles like "Successfully completed" or "Attempted to". Lead directly with the verb: "Decomposed OSB...", "Refactored UI...", "Fixed bug in...".
- **Weight by human engagement, not output volume.** Use session prompt counts (from Step 4.2) to determine where the human's attention actually went. An autonomous agent running for 4 hours is "dispatched work that produced X" — one sentence. A 5-minute interactive debugging session with 3 prompts is the real story. The reader wants to know what they thought about today, not what their agents did.
- **Use concrete details from user prompts, not abstract labels.** "Debugged PKB search for [[specific research question]]" tells a story. "[[Topic area]] PKB lookup" is a label. The `description` field from `user_prompt` timeline events contains the ground truth — use it.
- **Work type hierarchy — research leads.** This framework serves academic users. Research, writing, and analysis are the primary work; infrastructure and tooling exist to support them. When composing the story:
  1. Classify each session's work type: **research** (analysis, writing, methodology, data, literature), **academic** (teaching, supervision, review, service), **infrastructure** (framework, tooling, DevOps, PRs). Use the user's prompt text and project context as signals.
  2. Research and academic sessions lead the narrative, regardless of how many PRs merged or tasks were filed.
  3. Infrastructure work gets a brief sentence or parenthetical, not the lead. "3 PRs merged on framework tooling" is sufficient — don't enumerate them unless the user was interactively involved.
  4. If research sessions exist but produced no GitHub artifacts, that's normal — research produces understanding, not commits. Write about what was explored, decided, or advanced.
  5. If NO research work happened and the day was all infrastructure, note that honestly: "Infrastructure day — no research progress."

### Step 5.3.1: Update daily note frontmatter with narrative

After writing Today's Story to the work-date note, update that same note's frontmatter fields. This is the sole write point for the daily narrative — the cron synthesis script does not generate it. Read and write the work-date note, never "today's note" if they differ.

1. Adapt Today's Story from prose (Step 5.3) into 3-5 bullet points:
   - Second person ("you started...", "you got pulled into...")
   - Each bullet under 80 characters
   - Cover: what started, what got sidetracked, what remains undone
   - Weight by human engagement (prompt count from Step 4.2), not agent output volume. Lead with what the human interacted with, not what autonomous agents produced.
   - **Lead bullets with research/academic work.** Infrastructure gets last bullet position. If research sessions had high engagement (2+ prompts), they are always bullet #1.
2. Read the work-date note file
3. Update the YAML frontmatter fields:
   - `daily_narrative`: the 2-4 sentence prose summary (excluding "Dropped Threads" bullet)
   - `daily_story`: the bullet array from step 1
   - `narrative_generated`: ISO 8601 timestamp
4. Write the file back

### Step 5.4: Terminal Briefing Output

After updating the daily note, output a concise briefing to the terminal:

```
## Daily Summary (vN)

[Today's Story text from 5.3]

**Momentum**: [Summary of work since last run]
**Dropped**: [Titles of unfinished threads]

**Total Progress**: N PRs merged, N tasks completed.

Daily note updated at [path].
Use `/pull` to resume work.
```
