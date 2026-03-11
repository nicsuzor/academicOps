# Daily Note: Work Summary

## 5. Work Summary

After progress sync, generate a brief natural language summary of the day's work. This is the **key output** that the user sees both in the daily note and in the terminal. When running multiple times a day, emphasize recent momentum and context shifts.

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

Write a 2-4 sentence natural language summary to the `## Today's Story` section. This replaces (not appends to) the existing Today's Story content.

**Current Momentum**: If this is a repeat run, ensure the first sentence summarizes the work done **since the last update**.

**Dropped Threads**: If the path reconstruction identified "Abandoned Work", add a single bullet point under the story:

- **⚠ Dropped Threads**: "[Task Title]" (started in session [id] but unfinished).

**Style guide**:

- Write in past tense, first person plural or third person ("Merged 3 PRs..." / "The day focused on...")
- Lead with the most impactful work, not chronological order
- Mention specific PR numbers and task IDs for traceability
- If goals were set in Focus, note alignment or drift briefly

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
