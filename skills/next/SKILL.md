---
name: next
category: instruction
description: Get 2-3 task recommendations based on deadlines, variety, and momentum. ADHD-friendly task selection. Maintains daily.md Focus Dashboard.
allowed-tools: Read,Bash,Grep,Write,Edit
version: 2.0.0
permalink: skills-next
---

# Next Task Skill

Get intelligent task recommendations and maintain daily.md Focus Dashboard throughout the day.

## When to Use

- "What should I do next?"
- Coming back from a break or hyperfocus session
- Morning planning after email triage
- Switching between terminals and losing context

## Execution

### Step 1: Ensure Daily Note Exists

Check if today's daily note exists at `$ACA_DATA/sessions/YYYYMMDD-daily.md`.

**If missing**: Create from template at `skills/next/templates/daily.md`, replacing YYYY-MM-DD with today's date.

### Step 2: Update Focus Dashboard

Read today's daily note and update the Focus Dashboard section:

**Priority Burndown**: Query task data to count P0/P1/P2 tasks and their completion status.

```bash
cd $AOPS && uv run python skills/next/scripts/select_task.py
```

Use the `active_tasks` count and task priority distribution to generate:

```
P0 ████░░░░░░  2/5 → [[task-1]], [[task-2]]
P1 ██████░░░░  3/5 → [[task-3]]
P2 ░░░░░░░░░░  0/3
```

**Blocked**: Find tasks with status=waiting in task index and list them.

**Today's Journey**: Preserve existing entries (do not overwrite).

### Step 3: Gather Recommendations

Run the selection script:

```bash
cd $AOPS && uv run python skills/next/scripts/select_task.py
```

The script outputs JSON with 3 recommendations.

### Step 4: Present Options

Format the output as:

```markdown
## Task Recommendations

**Today so far**: [N] [project] items, [M] [project] items

### 1. PROBABLY SHOULD (deadline pressure)

**[Task Title]** - [reason]

- Due: [date] | Project: [project]

### 2. MIGHT ENJOY (different domain)

**[Task Title]** - [reason]

- Good counterweight to recent [project] work
- **Next steps** (from next_subtasks if present):
  - [ ] First actionable subtask
  - [ ] Second actionable subtask

### 3. QUICK WIN (build momentum)

**[Task Title]** - [reason]

- Estimated: 5-15 min

---

### Archive candidates (if any)

- **[Stale Task]** - [reason: past event / overdue 60+ days]
```

**Note**: The script extracts up to 3 unchecked subtasks for ANY task with multiple steps, making them immediately actionable. Stale tasks (past events >7 days, overdue >60 days) are excluded from recommendations and shown separately as archive candidates.

### Step 5: User Decision

After presenting, ask:

```
What sounds right?
```

### Step 6: Handle Selection

When user picks a task:

1. **Read** today's daily note
2. **Add entry** to Today's Journey table (most recent at top):

```markdown
| Time  | Task                                     | Status   |
| ----- | ---------------------------------------- | -------- |
| HH:MM | [[task-slug]] (P[n]) - brief description | → active |
```

3. **Update status** of any previously active task to `paused`
4. **Write** updated daily note

**Status values**: `→ active` (current focus), `✓ done`, `paused`, `blocked`

## Focus Dashboard Sections (Owned by /next)

| Section           | Purpose                                  | Data Source                 |
| ----------------- | ---------------------------------------- | --------------------------- |
| Priority Burndown | P0/P1/P2 task counts with progress bars  | Task index                  |
| Today's Journey   | Timestamped log of tasks worked on today | User selections             |
| Blocked           | Tasks waiting on external dependencies   | Task index (status=waiting) |

**Session-insights owns**: Today's Story, Project Accomplishments, Session Log, Session Timeline, Session Insights, Abandoned Todos.

## Selection Logic

| Category   | Priority                                                           |
| ---------- | ------------------------------------------------------------------ |
| **Should** | Overdue > Due today > Due this week > P0 tasks                     |
| **Enjoy**  | Different project from today's dominant work, creative/substantive |
| **Quick**  | Action items, approvals, responses, single-step tasks              |

### Framework Work Warning

**Framework/aops work is meta-work, not real productivity.** When presenting recommendations:

1. If today's work is dominated by `aops`/`academicOps` (3+ items), explicitly note: "Heavy framework day - consider actual tasks"
2. ENJOY recommendation should prioritize NON-framework tasks when aops is dominant
3. Never recommend more framework work as "variety" from framework work

## Arguments

- None (uses current date automatically)
- `--date YYYYMMDD` - Check recommendations for different date (testing)

**Project filtering**: If user specifies a project (e.g., "aops tasks", "OSB work"), filter script output to only show tasks matching that project before presenting.

## Output

Returns recommendations to present to user. Updates daily.md Focus Dashboard on every run.
