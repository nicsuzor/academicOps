---
title: Morning Briefing Skill
type: spec
category: spec
status: draft
permalink: morning-briefing-skill
tags:
  - spec
  - skill
  - morning
  - briefing
  - email
  - tasks
  - adhd
---

# Morning Briefing Skill

**Status**: Draft
**Priority**: P1 (ADHD accommodation: zero-friction daily orientation)

**Files governed**:

- `$AOPS/skills/morning/SKILL.md`
- `$AOPS/skills/morning/scripts/gather_briefing_data.py`

## User Story

**As** Nic (academic with ADHD starting a work day),
**I want** a comprehensive morning briefing that shows everything I need to know,
**So that** I can orient quickly, make informed focus decisions, and not miss urgent items buried in email or across projects.

## Solution

A `/morning` skill that produces a single synthesized briefing containing:

1. **Email Triage** - New tasks from email + FYI notifications needing acknowledgment
2. **Project Activity** - Recent work on each major project (last 3 calendar days)
3. **Priority Discussion** - Task recommendations with rationale for today's focus

## Data Sources

| Source                                               | What We Extract                                                |
| ---------------------------------------------------- | -------------------------------------------------------------- |
| Outlook MCP                                          | Recent emails (last 24h): new tasks created, FYI notifications |
| `$ACA_DATA/sessions/YYYYMMDD-daily.md` (last 3 days) | Accomplishments by project                                     |
| `$ACA_DATA/dashboard/synthesis.json`                 | Narrative, recent session projects                             |
| `$ACA_DATA/tasks/index.json`                         | All tasks with priority, due, project                          |
| `/next` skill output                                 | 3 ranked recommendations                                       |

## Output Format

```markdown
# Morning Briefing - [Date]

## Email Triage

### New Tasks

- **[Task Title]** - [Project] - from: [sender]
  [Or: No new tasks from email]

### FYI (Acknowledge to Archive)

[Use AskUserQuestion with multiSelect for batch acknowledgment]

## Recent Project Activity

### [Project] (last: [date])

- [accomplishment]
- State: [current state/blockers]

[Top 3-5 projects by recency]

## Today's Focus

**SHOULD**: [Task] - [deadline reason]
**ENJOY**: [Task] - [variety reason]
**QUICK**: [Task] - [momentum reason]

[1-2 sentence rationale for suggested sequencing]
```

## Workflow

```
1. Ensure daily note exists (create from /next if missing)
2. Fetch emails via Outlook MCP (last 24h)
   → FAIL-FAST if Outlook unavailable: report error, halt
3. Load synthesis.json (graceful: skip section if missing)
4. Load last 3 daily notes (graceful: show what exists)
5. Load task index via /next skill
6. LLM synthesizes briefing
7. Present FYI emails for batch acknowledgment
8. Archive selected FYIs via mcp__outlook__messages_move
```

**Failure behavior**: Outlook is required (primary value is email triage). Other sources degrade gracefully.

**Duplicate handling**: Track briefed email entry_ids in daily note `briefed_emails` field. Skip emails already briefed today.

**Relationship to `/email`**: `/morning` focuses on triage (FYI vs action-needed classification). For emails requiring tasks, user runs `/email` on specific items. No duplication—different purposes.

## Implementation

### Skill Location

`$AOPS/skills/morning/SKILL.md`

### Invocation

```
/morning
```

### Script

`$AOPS/skills/morning/scripts/gather_briefing_data.py`

Gathers data from 5 sources into structured JSON for LLM synthesis. This complexity justifies a script (per H24).

### FYI Detection

LLM classifies each email semantically:

- **FYI**: Informational, no action required, but should be seen before archiving
- **Task**: Requires action → flag for `/email` processing
- **Skip**: Automated, bulk, already handled
- **Uncertain**: Present to user with "Is this FYI?" prompt

No keyword matching. Agent reads email content and classifies by intent.

**Confidence handling**: When uncertain, present email to user for classification rather than guessing.

### FYI Acknowledgment

Use `AskUserQuestion` with `multiSelect: true` to present FYI emails as checkboxes. Selected items archived via `mcp__outlook__messages_move` to archive folder.

**Empty state**: If no FYI emails, skip this section (don't ask empty question).

### Edge Cases

- **No emails (24h)**: Show "Inbox clear" in email section, continue to project activity
- **No daily notes**: Show "No recent session activity" in project section
- **No synthesis.json**: Skip narrative, show tasks only
- **Second run same day**: Skip already-briefed emails (tracked in daily note)

## Acceptance Criteria

- [ ] **AC1**: `/morning` produces briefing in <30 seconds
- [ ] **AC2**: Email section shows new tasks and FYI notifications
- [ ] **AC3**: Project activity shows 3-5 active projects with recency
- [ ] **AC4**: Task recommendations include rationale
- [ ] **AC5**: FYI acknowledgment archives emails via AskUserQuestion
- [ ] **AC6**: Graceful degradation when data sources unavailable

## Dependencies

- Outlook MCP (exists)
- Daily notes (exists)
- synthesis.json (exists)
- `/next` skill (exists)
- Task index (exists)
