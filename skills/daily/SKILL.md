---
name: daily
category: instruction
description: Daily note lifecycle - morning briefing, task recommendations, session sync. SSoT for daily note structure.
allowed-tools: Read,Bash,Grep,Write,Edit,AskUserQuestion,mcp__outlook__messages_list_recent,mcp__outlook__messages_get,mcp__outlook__messages_move
version: 1.0.0
permalink: skills-daily
---

# Daily Note Skill

Manage daily note lifecycle: morning briefing, task recommendations, and session sync.

## Modes

| Invocation     | Purpose                                                     |
| -------------- | ----------------------------------------------------------- |
| `/daily`       | Morning briefing (default) - email triage + recommendations |
| `/daily focus` | Task recommendations only (replaces /next)                  |
| `/daily sync`  | Update daily note from session JSONs                        |

## Daily Note Structure (SSoT)

Location: `$ACA_DATA/sessions/YYYYMMDD-daily.md`

```markdown
# Daily Summary - YYYY-MM-DD

## Focus

Priority items set by user. Morning briefing updates this.

## Today's Story

Synthesized narrative from session summaries (2-3 sentences).

## Focus Dashboard

P0 ████░░░░░░ 4/14 → [Task1], [Task2]
P1 ██████░░░░ 10/14 → [Task3] (-8d)

[Task1]: [[task-file-slug]]

## Session Log

| Session | Project | Summary           |
| ------- | ------- | ----------------- |
| abc1234 | writing | Brief description |

## Session Timeline

| Time  | Session | Terminal | Project | Activity     |
| ----- | ------- | -------- | ------- | ------------ |
| 10:15 | abc1234 | writing  | aops    | Started work |

### Terminal Overwhelm Analysis

Pattern analysis of context switches and interruptions.

## [[project-name]] → [[projects/project-name]]

Scheduled: ██████░░░░ 6/10 | Unscheduled: 3 items

- [x] Accomplishment from sessions
- [ ] Pending task

## Abandoned Todos

Tasks not completed, carried to tomorrow.
```

## Section Ownership

| Section                 | Owner          | Updated By                  |
| ----------------------- | -------------- | --------------------------- |
| Focus                   | User           | `/daily` (morning briefing) |
| Today's Story           | `/daily sync`  | Session JSON synthesis      |
| Focus Dashboard         | `/daily focus` | Script output               |
| Session Log/Timeline    | `/daily sync`  | Session JSON synthesis      |
| Project Accomplishments | `/daily sync`  | Session JSON synthesis      |
| Abandoned Todos         | `/daily sync`  | End-of-day                  |

## Mode: `/daily` (Morning Briefing)

Default mode. Run at start of day for orientation.

### Step 1: Ensure Daily Note Exists

Check `$ACA_DATA/sessions/YYYYMMDD-daily.md`.

**If missing**: Create from template (see Daily Note Structure above), then:

1. Read yesterday's daily note
2. Copy "Abandoned Todos" to "## Carryover from Yesterday" section
3. Note overdue items from yesterday's Focus Dashboard

### Step 2: Email Triage

Fetch recent emails via Outlook MCP:

```
mcp__outlook__messages_list_recent(limit=50, folder="inbox")
```

**Classify each email** (LLM semantic classification, not keyword matching per AXIOM #30):

- **FYI**: Informational, no action needed, but should see before archiving
- **Task**: Requires action → flag for `/email` processing
- **Skip**: Automated, bulk, already handled
- **Uncertain**: Present to user for classification

### Step 3: Present FYI Emails for Acknowledgment

**First**, display FYI emails with enough detail for informed decisions:

- Sender
- Subject
- Brief preview (first 1-2 sentences of body)

**Then**, use `AskUserQuestion` with `multiSelect: true` to ask which emails to archive.

Selected items archived via `mcp__outlook__messages_move(entry_id, folder_path="Archive")`.

**Empty state**: If no FYI emails, skip this section.

### Step 4: Load Recent Activity

Read last 3 daily notes to show project activity summary:

- Which projects had work recently
- Current state/blockers per project

### Step 5: Task Recommendations

Run `/daily focus` workflow (Step 2-5 from that mode) to get task recommendations.

### Step 6: Present Morning Briefing

```markdown
# Morning Briefing - [Date]

## Email Triage

### New Tasks

- **[Task]** - [Project] - from: [sender]

### FYI (Acknowledge to Archive)

[AskUserQuestion checkboxes]

## Recent Project Activity

### [Project] (last: [date])

- [accomplishment]
- State: [current state/blockers]

## Today's Focus

**SHOULD**: [Task] - [deadline reason]
**ENJOY**: [Task] - [variety reason]
**QUICK**: [Task] - [momentum reason]

[1-2 sentence rationale for suggested sequencing]
```

## Mode: `/daily focus` (Task Recommendations)

Get intelligent task recommendations. Replaces `/next` skill.

### Prerequisite: Daily Note

Same as morning briefing Step 1 - ensure daily note exists.

### Step 2: Load Task Data

```bash
cd $AOPS && uv run python skills/tasks/scripts/select_task.py
```

Output:

- `active_task_count`: Total active tasks
- `todays_work`: Project → count mapping
- `priority_distribution`: P0/P1/P2/P3 counts
- `stale_candidates`: Tasks to suggest archiving
- `active_tasks`: Full task list

### Step 3: Update Focus Dashboard

Update Focus Dashboard section in daily note using `priority_distribution`.

**Reference-style wikilinks** for scannability:

```
P0 ████░░░░░░  4/14 → [Task1], [Task2]
P1 ██████░░░░  10/14 → [Task3] (-8d)

[Task1]: [[task-file-slug]]
```

### Step 4: Reason About Recommendations

Select 3 recommendations using judgment:

**SHOULD (deadline/commitment pressure)**:

- Check `days_until_due` - negative = overdue
- Priority: overdue → due today → due this week → P0 without dates

**ENJOY (variety/energy)**:

- Check `todays_work` - if one project has 3+ items, recommend different project
- Look for: papers, research, creative tasks
- Avoid immediate deadlines (prefer >7 days out)

**QUICK (momentum builder)**:

- Simple tasks: `subtasks_total` = 0 or 1
- Title signals: approve, send, confirm, respond, check
- Aim for <15 min

**Framework work warning**: If `academicOps`/`aops` has 3+ items in `todays_work`:

1. Note: "Heavy framework day - consider actual tasks"
2. ENJOY must be non-framework work

### Step 5: Present Recommendations

```markdown
## Task Recommendations

**Today so far**: [N] [project] items, [M] [project] items

### 1. PROBABLY SHOULD (deadline pressure)

**[Task Title]** - [reasoning]

- Due: [date] | Priority: P[n] | Project: [project]

### 2. MIGHT ENJOY (different domain)

**[Task Title]** - [reasoning]

- Good counterweight to recent [project] work

### 3. QUICK WIN (build momentum)

**[Task Title]** - [reasoning]

- Should take: 5-15 min

### Archive candidates

- **[Stale Task]** - [reason]
```

Ask: "What sounds right?"

When user picks, use `Skill(skill="tasks")` to update status.

## Mode: `/daily sync` (Session Sync)

Update daily note from session JSON files. Run after sessions complete or periodically.

### Step 1: Find Session JSONs

```bash
ls $ACA_DATA/dashboard/sessions/YYYYMMDD*.json 2>/dev/null
```

### Step 2: Load and Merge Sessions

Read each session JSON. Extract:

- Session ID, project, summary
- Accomplishments
- Timeline entries
- Skill compliance metrics

### Step 3: Verify Descriptions

**CRITICAL**: Gemini mining may hallucinate. Cross-check accomplishment descriptions against actual changes (git log, file content). Per AXIOMS #2, do not propagate fabricated descriptions.

### Step 4: Update Daily Note Sections

Using **Edit tool** (not Write) to preserve existing content:

**Today's Story**: Synthesize narrative from session summaries.

**Session Log**: Add/update session entries.

**Session Timeline**: Build from conversation_flow timestamps.

**Project Accomplishments**: Add `[x]` items under project headers.

**Progress metrics** per project:

- **Scheduled**: Tasks with `scheduled: YYYY-MM-DD` matching today
- **Unscheduled**: Accomplishments not matching scheduled tasks
- Format: `Scheduled: ██████░░░░ 6/10 | Unscheduled: 3 items`

### Step 5: Update synthesis.json

Write `$ACA_DATA/dashboard/synthesis.json`:

```json
{
  "generated": "ISO timestamp",
  "date": "YYYYMMDD",
  "sessions": {
    "total": N,
    "by_project": {"aops": 2, "writing": 1},
    "recent": [{"session_id": "...", "project": "...", "summary": "..."}]
  },
  "narrative": ["Session summary 1", "Session summary 2"],
  "accomplishments": {
    "count": N,
    "summary": "brief text",
    "items": [{"project": "aops", "item": "Completed X"}]
  },
  "next_action": {"task": "P0 task", "reason": "Highest priority"},
  "alignment": {"status": "on_track|blocked|drifted", "note": "..."},
  "waiting_on": [{"task": "...", "blocker": "..."}],
  "skill_insights": {"compliance_rate": 0.75, "top_context_gaps": []},
  "session_timeline": [{"time": "10:15", "session": "...", "activity": "..."}]
}
```

## Scripts

| Script                   | Purpose                               |
| ------------------------ | ------------------------------------- |
| `scripts/select_task.py` | Prepare task data for recommendations |

## Arguments

- None (uses current date)
- `--date YYYYMMDD` - Process different date (testing)

## Error Handling

- **Outlook unavailable**: Skip email triage, continue with recommendations
- **No session JSONs**: Skip sync, note "No sessions to sync"
- **No tasks**: Present empty state, offer to run `/tasks`
