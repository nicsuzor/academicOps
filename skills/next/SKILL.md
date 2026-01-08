---
name: next
category: instruction
description: Get 2-3 task recommendations using LLM reasoning. ADHD-friendly task selection. Maintains daily.md Focus Dashboard.
allowed-tools: Read,Bash,Grep,Write,Edit
version: 3.0.0
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

**If missing**:

1. Create from template at `skills/next/templates/daily.md`, replacing YYYY-MM-DD with today's date
2. Read yesterday's daily note (`YYYYMMDD-1-daily.md`)
3. Copy over "Abandoned Todos" as a new "## Carryover from Yesterday" section
4. Note any overdue items from yesterday's Priority Burndown

### Step 2: Load Task Data

Run the data preparation script:

```bash
cd $AOPS && uv run python skills/tasks/scripts/select_task.py
```

This outputs ALL active tasks with metadata. You will reason about selection.

Output includes:

- `active_task_count`: Total active tasks
- `todays_work`: Project → count mapping for today's accomplishments
- `priority_distribution`: P0/P1/P2/P3 counts
- `stale_candidates`: Tasks to suggest for archiving
- `active_tasks`: Full task list sorted by priority then due date

### Step 3: Update Focus Dashboard

Use `priority_distribution` from script output to update the Focus Dashboard section in today's daily note.

**Use reference-style wikilinks** - short labels in body, full links in endnotes section:

```
P0 ████░░░░░░  4/14 → [Lucinda extension], [OSB receipts]
P1 ██████░░░░  10/14 → [ADMS report] (-8d)
P2 ░░░░░░░░░░  0/14

[Lucinda extension]: [[20260106-approve-lucinda-nelson-hdr-extension-request]]
[OSB receipts]: [[Process Oversight Board receipts]]
[ADMS report]: [[20251223-complete-adms-clever-reporting-for-2025]]
```

This keeps the dashboard scannable while preserving Obsidian graph links.

### Step 4: Reason About Recommendations

Review the task data and select 3 recommendations using YOUR judgment:

**SHOULD (deadline/commitment pressure)**:

- Look at `days_until_due` field - negative means overdue
- Consider priority level (P0 tasks are critical)
- Prefer: overdue → due today → due this week → P0 without dates
- If title is unclear, read the task file for context

**ENJOY (variety/energy)**:

- Check `todays_work` - which project dominated today?
- If one project has 3+ items, recommend a DIFFERENT project
- Look for substantive work: papers, research, creative tasks
- Check tags for: writing, research, paper, creative
- Avoid immediate deadlines (prefer >7 days out)

**QUICK (momentum builder)**:

- Look for `subtasks_total` = 0 or 1 (simple tasks)
- Title signals: approve, send, confirm, respond, check
- Tasks with `subtasks_done` close to `subtasks_total`
- Aim for <15 min tasks

**For any task**: Read `$ACA_DATA/[file]` if you need more context than metadata provides.

### Step 4b: Framework Work Warning

**Framework/aops work is meta-work, not real productivity.**

Check `todays_work` - if `academicOps` or `aops` has 3+ items:

1. Explicitly note: "Heavy framework day - consider actual tasks"
2. ENJOY recommendation MUST be non-framework work
3. Never recommend more framework work as "variety" from framework work

### Step 4c: Check for Prioritized Tasks

If `priority_distribution` shows P0=0 AND P1=0, ask the user:

```
No tasks are prioritized for today. Would you like to:
1. Pick from these recommendations anyway
2. Set priorities first (I'll use /tasks to help select focus tasks)
```

Use `AskUserQuestion` tool. If user chooses option 2, invoke `Skill(skill="tasks")`.

### Step 5: Present Options

Format your selections as:

```markdown
## Task Recommendations

**Today so far**: [N] [project] items, [M] [project] items

### 1. PROBABLY SHOULD (deadline pressure)

**[Task Title]** - [YOUR reasoning about why this is urgent]

- Due: [date] | Priority: P[n] | Project: [project]

### 2. MIGHT ENJOY (different domain)

**[Task Title]** - [YOUR reasoning about why this provides variety]

- Good counterweight to recent [project] work
- **Next steps** (if next_subtasks present):
  - [ ] First actionable subtask
  - [ ] Second actionable subtask

### 3. QUICK WIN (build momentum)

**[Task Title]** - [YOUR reasoning about why this is quick]

- Should take: 5-15 min

---

### Archive candidates (if stale_candidates not empty)

- **[Stale Task]** - [reason from stale_candidates]
```

### Step 6: User Decision

After presenting, ask:

```
What sounds right?
```

### Step 7: Handle Selection

When user picks a task, use `Skill(skill="tasks")` to update task status if needed.

## Focus Dashboard Sections (Owned by /next)

| Section           | Purpose                                 | Data Source                  |
| ----------------- | --------------------------------------- | ---------------------------- |
| Priority Burndown | P0/P1/P2 task counts with progress bars | Script priority_distribution |
| Blocked           | Tasks waiting on external dependencies  | Task index (status=waiting)  |

**Session-insights owns**: Today's Story, Project Accomplishments, Session Log, Session Timeline, Session Insights, Abandoned Todos.

## Arguments

- None (uses current date automatically)
- `--date YYYYMMDD` - Check recommendations for different date (testing)

**Project filtering**: If user specifies a project (e.g., "aops tasks", "OSB work"), filter the active_tasks to only that project before reasoning.

## Output

Returns recommendations with YOUR reasoning to present to user. Updates daily.md Focus Dashboard on every run.
