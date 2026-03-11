---
title: Task Selector Skill
type: spec
category: spec
status: implemented
permalink: task-selector-skill
tags: [spec, tasks, adhd, focus, automation]
---

# Task Selector Skill

**Status**: Implemented (2026-01-06)
**Priority**: P1 (core ADHD accommodation)

## User Story

**As** Nic (academic with ADHD who gets pulled between terminals and projects),
**I want** to ask "what should I do next?" and get 2-3 ranked options,
**So that** I can quickly re-engage with work without decision paralysis or always defaulting to the most urgent thing.

## The Problem

Current `next_action` in synthesis.json just returns "first P0 task" or "soonest due date". This is mechanical and ignores:

- What the user has been doing (burnout/variety)
- Energy levels (quick win vs deep work)
- The ADHD need for novelty alongside obligation

## Solution

A `/next` skill that:

1. Gathers context (task index, today's accomplishments, synthesis.json)
2. Applies selection heuristics
3. Presents 2-3 options categorized by type

## Selection Categories

| Category   | Label             | Selection Logic                                                                |
| ---------- | ----------------- | ------------------------------------------------------------------------------ |
| **Should** | "Probably should" | Deadline pressure: overdue > due today > due this week > P0                    |
| **Enjoy**  | "Might enjoy"     | Different domain from recent work, substantive/creative, no immediate deadline |
| **Quick**  | "Quick win"       | Estimated <15 min, clears cognitive load, builds momentum                      |

## Selection Heuristics

### H1: Variety Over Tunnel Vision

If user has done 5+ items in one project today, recommend "Enjoy" from a _different_ project.

### H2: Deadline Gravity

Overdue tasks always appear in "Should" regardless of priority. Due-today gets highest weight.

### H3: Quick Win Threshold

Tasks with:

- `classification: Action` or title containing "respond", "approve", "confirm"
- No subtasks OR subtasks all completed except one
- Estimated effort = low/medium

### H4: Deep Work Detection

Tasks with:

- `classification: Create` or `Review`
- Tags containing "paper", "writing", "research"
- Multiple subtasks

## Data Sources

| Source                                 | What We Extract                                       |
| -------------------------------------- | ----------------------------------------------------- |
| `$ACA_DATA/tasks/index.json`           | All tasks with priority, due, project, status         |
| `$ACA_DATA/sessions/YYYYMMDD-daily.md` | Today's accomplishments by project (for variety calc) |
| `$ACA_DATA/dashboard/synthesis.json`   | Recent session projects (for variety calc)            |

## Output Format

```markdown
## 🎯 Task Recommendations

**Today so far**: 17 aops items, 3 writing items

### 1. PROBABLY SHOULD (deadline)

**[Task Title]** - [reason]

- Due: [date] | Project: [project]
- **Next steps** (if task has subtasks):
  - [ ] First unchecked subtask

### 2. MIGHT ENJOY (variety)

**[Task Title]** - [reason]

- Different domain from recent work
- **Next steps**:
  - [ ] First unchecked subtask
  - [ ] Second unchecked subtask

### 3. QUICK WIN (momentum)

**[Task Title]** - [reason]

- Estimated: 5-15 min

---

### 🗑️ Archive candidates

- **[Stale Task]** - [reason: past event / overdue 60+ days]
```

**Notes**:

- All recommendations include up to 3 next subtasks from task file (making any multi-step task actionable)
- Stale tasks (past events >7 days, overdue >60 days) are excluded from recommendations and shown separately

## Implementation

### Skill Location

`$AOPS/skills/next/SKILL.md`

### Script

`$AOPS/skills/next/scripts/select_task.py`

The script:

1. Loads index.json, daily.md, synthesis.json
2. Applies selection heuristics
3. Returns JSON with 3 recommendations

### Invocation

```
/next
```

Or automatically suggested by SessionStart hook after morning email triage.

## Acceptance Criteria

- [x] **AC1**: `/next` returns 3 categorized task options
- [x] **AC2**: "Should" respects deadline hierarchy (overdue > today > this week > P0)
- [x] **AC3**: "Enjoy" favors different project from today's dominant work
- [x] **AC4**: "Quick" filters for low-effort actionable items
- [x] **AC5**: Output is concise (fits in terminal without scrolling)

## Future Enhancements

- Time-of-day awareness (morning = deep work, afternoon = quick wins)
- Learning from what user actually picks (reinforce good matches)
- Integration with calendar (block awareness)
