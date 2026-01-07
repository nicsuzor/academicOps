---
name: next
category: instruction
description: Get 2-3 task recommendations based on deadlines, variety, and momentum. ADHD-friendly task selection.
allowed-tools: Read,Bash,Grep
version: 1.0.0
permalink: skills-next
---

# Next Task Skill

Get intelligent task recommendations when you need to decide what to work on.

## When to Use

- "What should I do next?"
- Coming back from a break or hyperfocus session
- Morning planning after email triage
- Switching between terminals and losing context

## Execution

### Step 1: Gather Context

Run the selection script:

```bash
cd $AOPS && uv run python skills/next/scripts/select_task.py
```

The script outputs JSON with 3 recommendations.

### Step 2: Present Options

Format the output as:

```markdown
## 🎯 Task Recommendations

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

### 🗑️ Archive candidates (if any)

- **[Stale Task]** - [reason: past event / overdue 60+ days]
```

**Note**: The script extracts up to 3 unchecked subtasks for ANY task with multiple steps, making them immediately actionable. Stale tasks (past events >7 days, overdue >60 days) are excluded from recommendations and shown separately as archive candidates.

### Step 3: User Decision

After presenting, ask:

```
What sounds right?
```

If user picks one, update the daily.md "Active Now" section to reflect what they're working on.

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

**Project filtering**: If user specifies a project (e.g., "aops tasks", "OSB work"), filter script output to only show tasks matching that project before presenting. The script doesn't support `--project` yet (see Issue #294).

## Output

Returns recommendations to present to user. Does NOT automatically start tasks.
