# Daily Note: Work Summary

## 5. Work Summary

After progress sync, generate a brief natural language summary of the day's work. This is the **key output** that the user sees both in the daily note and in the terminal.

### Step 5.1: Gather Inputs

Collect from the sections already populated:

- **Merged PRs** (from Step 4.2.5): titles and count
- **Session accomplishments** (from Step 4.2): what was done in each session
- **Completed tasks** (from Step 4.1.5): tasks closed today
- **Focus goals** (from `### My priorities`): what the user intended to do

### Step 5.2: Generate Today's Story

Write a 2-4 sentence natural language summary to the `## Today's Story` section. This replaces (not appends to) the existing Today's Story content.

**Style guide**:

- Write in past tense, first person plural or third person ("Merged 3 PRs..." / "The day focused on...")
- Lead with the most impactful work, not chronological order
- Mention specific PR numbers and task IDs for traceability
- Note any significant merges, completions, or milestones
- If goals were set in Focus, note alignment or drift briefly

**Example**:

```markdown
## Today's Story

Consolidated the PR review and merge workflows into a single pipeline (#415), fixing the broken LGTM merge trigger. Updated the daily skill to include GitHub merge tracking and natural language summaries. Three PRs merged today, all related to the academicOps framework infrastructure push. Focus stayed on framework work despite planning to tackle the OSB review — that carries to tomorrow.
```

### Step 5.3: Terminal Briefing Output

After updating the daily note, output a concise briefing to the terminal:

```
## Daily Summary

[Today's Story text from 5.2]

**Merged today**: N PRs (#123, #124, #125)
**Sessions**: N across [projects]
**Tasks completed**: N

Daily note updated at [path].
Daily planning complete. Use `/pull` to start work.
```

This gives the user a quick snapshot without needing to open the note.
