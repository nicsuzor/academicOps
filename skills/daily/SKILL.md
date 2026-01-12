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

Location: `$ACA_DATA/sessions/YYYYMMDD-daily.md`

## Section Ownership

| Section                 | Owner    | Updated By             |
| ----------------------- | -------- | ---------------------- |
| Focus                   | User     | `/daily` workflow      |
| Today's Story           | `/daily` | Session JSON synthesis |
| Focus Dashboard         | `/daily` | Script output          |
| Session Log/Timeline    | `/daily` | Session JSON synthesis |
| Project Accomplishments | `/daily` | Session JSON synthesis |
| Abandoned Todos         | `/daily` | End-of-day             |

## 1. Create note

Check `$ACA_DATA/sessions/YYYYMMDD-daily.md`.

**If missing**: Create from template (see Daily Note Structure above), then:

1. Read the previous working day's daily note
2. Identify any incomplete tasks and copy to "## Carryover from Yesterday" section
3. Copy "Abandoned Todos" to "## Carryover from Yesterday" section
4. Note overdue items from yesterday's Focus Dashboard

### 1.2: Load Recent Activity

Read last 3 daily notes to show project activity summary:

- Which projects had work recently
- Current state/blockers per project

## 2. Update daily briefing

### 2.1: Email Triage

Fetch recent emails via Outlook MCP:

```
mcp__outlook__messages_list_recent(limit=50, folder="inbox")
```

**Before flagging as Task**: Check sent mail for replies to avoid flagging already-handled items:

```
mcp__outlook__messages_list_recent(limit=20, folder="sent")
```

If inbox email subject matches a sent reply (Re: prefix), classify as **Skip** (already handled).

**Classify each email** (LLM semantic classification, not keyword matching per AXIOM #30):

- **FYI**: Informational, no action needed, but should see before archiving
- **Task**: Requires action AND no sent reply exists → flag for `/email` processing. This includes emails with deliverables requiring processing (attached documents, spreadsheets, files to upload/integrate), even if the email tone is informational.
- **Skip**: Automated, bulk, or already handled (sent reply exists)
- **Uncertain**: Present to user for classification

### 2.2: FYI Content in Daily Note

**Goal**: User reads FYI content in the daily note itself, not by opening emails.

**Thread grouping**: Group emails by conversation thread (same subject minus Re:/Fwd:). Present threads as unified summaries, not individual emails.

**For each FYI thread/item**, fetch full content with `mcp__outlook__messages_get` and include:

- Thread participants and who said what (if multiple contributors)
- **Actual content**: The key information - quote directly for short emails, summarize for long ones

**Format in briefing**:

```markdown
## FYI

### [Thread Topic]

[Participants] discussed [topic]. [Key content/decision/info].

> [Direct quote if short]

### [Single Email Topic]

From [sender]: [Actual content or summary]
```

**After presenting**: Use `AskUserQuestion` to ask which to archive.

**Empty state**: If no FYI emails, skip this section.

## 3. Today's Focus - Task Recommendations

Review tasks and update the template to spotlight focus items for the day.

### 3.1: Load Task Data

```bash
cd $AOPS && uv run python skills/tasks/scripts/select_task.py
```

Output:

- `active_task_count`: Total active tasks
- `todays_work`: Project → count mapping
- `priority_distribution`: P0/P1/P2/P3 counts
- `stale_candidates`: Tasks to suggest archiving
- `active_tasks`: Full task list

### 3.2: Update Focus Dashboard

Update Focus Dashboard section in daily note using `priority_distribution`.

**Reference-style wikilinks** for scannability:

```
P0 ████░░░░░░  4/14 → [Task1], [Task2]
P1 ██████░░░░  10/14 → [Task3] (-8d)

[Task1]: [[task-file-slug]]
```

### 3.3: Reason About Recommendations

Select 10 recommendations using judgment (approx 2 per category):

**SHOULD (deadline/commitment pressure)**:

- Check `days_until_due` - negative = overdue
- Priority: overdue → due today → due this week → P0 without dates

**DEEP (long-term goal advancement)**:

- Tasks linked to strategic objectives or major project milestones
- Look for: research, design, architecture, foundational work
- Prefer tasks that advance bigger goals, not just maintain status quo
- Avoid immediate deadlines (prefer >7 days out or no deadline)
- Should have meaningful impact on long-term outcomes

**ENJOY (variety/energy)**:

- Check `todays_work` - if one project has 3+ items, recommend different project
- Look for: papers, research, creative tasks
- Avoid immediate deadlines (prefer >7 days out)

**QUICK (momentum builder)**:

- Simple tasks: `subtasks_total` = 0 or 1
- Title signals: approve, send, confirm, respond, check
- Aim for <15 min

**UNBLOCK (remove impediments)**:

- Tasks that unblock other work or team members
- Infrastructure/tooling improvements
- Dependency resolution, blocked issues
- Look for: tasks marked with blocker status, tasks other work depends on
- Consider technical debt that's slowing down current work

**Framework work warning**: If `academicOps`/`aops` has 3+ items in `todays_work`:

1. Note: "Heavy framework day - consider actual tasks"
2. ENJOY must be non-framework work

### 3.4: Present Recommendations

```markdown
## Task Recommendations

**Today so far**: [N] [project] items, [M] [project] items

## Today's Focus

**SHOULD**: [Task] - [deadline reason]
**DEEP**: [Task] - [concrete task that moves us towards a bigger longer-term goal]
**ENJOY**: [Task] - [variety reason]
**QUICK**: [Task] - [momentum reason]
**UNBLOCK**: [Task] - [concrete issue that is blocking us or others]

[1-2 sentence rationale for suggested sequencing]
```

### 3.5: Present candidate tasks to archives

```
- **[Stale Task]** - [reason]
```

Ask: "What sounds right?"

When user picks, use `Skill(skill="tasks")` to update status.

### 4. Daily progress

Update daily note from session JSON files. Run after sessions complete or periodically.

### Step 4.1: Find Session JSONs

```bash
ls $ACA_DATA/dashboard/sessions/YYYYMMDD*.json 2>/dev/null
```

### Step 4.2: Load and Merge Sessions

Read each session JSON. Extract:

- Session ID, project, summary
- Accomplishments
- Timeline entries
- Skill compliance metrics

### Step 4.3: Verify Descriptions

**CRITICAL**: Gemini mining may hallucinate. Cross-check accomplishment descriptions against actual changes (git log, file content). Per AXIOMS #2, do not propagate fabricated descriptions.

### Step 4.4: Update Daily Note Sections

Using **Edit tool** (not Write) to preserve existing content:

**Today's Story**: Synthesize narrative from session summaries.

- format in dot points, but use prose to provide detail

**Session Log**: Add/update session entries.

**Session Timeline**: Build from conversation_flow timestamps.

**Project Accomplishments**: Add `[x]` items under project headers.

**Progress metrics** per project:

- **Scheduled**: Tasks with `scheduled: YYYY-MM-DD` matching today
- **Unscheduled**: Accomplishments not matching scheduled tasks
- Format: `Scheduled: ██████░░░░ 6/10 | Unscheduled: 3 items`

### Step 4.5: Update synthesis.json

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

## Error Handling

- **Outlook unavailable**: Skip email triage, continue with recommendations
- **No session JSONs**: Skip sync, note "No sessions to sync"
- **No tasks**: Present empty state, offer to run `/tasks`

## Daily Note Structure (SSoT)

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

## Abandoned tasks

Tasks not completed, carried to tomorrow.
```
