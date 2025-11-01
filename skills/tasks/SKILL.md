---
name: tasks
description: This skill provides expertise for task management operations using the academicOps task scripts. Use when agents or subagents need to create, view, update, or archive tasks in the knowledge base. Includes prioritization framework, duplicate checking protocols, and strategic alignment enforcement.
---

# Tasks: Task Management Expertise

## Overview

This skill provides the single point of expertise for interacting with the academicOps task management system. It documents HOW to use the task scripts located at `~/.claude/skills/scribe/scripts/` for creating, viewing, updating, and archiving tasks.

**Agents and subagents should use this skill** (not implement task management themselves) to ensure consistent task handling across the system.

## Task Scripts Reference

All task scripts are located at `~/.claude/skills/scribe/scripts/` and must be invoked with `uv run python`:

- **`task_add.py`** - Create new tasks
- **`task_view.py`** - View and search tasks (detailed)
- **`task_index.py`** - Compact task overview
- **`task_process.py`** - Update or archive tasks

## Core Task Operations

### 1. Check for Duplicates (ALWAYS DO THIS FIRST)

Before creating any task, ALWAYS check for duplicates:

```bash
uv run python ~/.claude/skills/scribe/scripts/task_view.py --per-page=50
```

Review the output and check `$ACADEMICOPS_PERSONAL/data/views/current_view.json` for existing similar tasks.

### 2. Create Task

```bash
uv run python ~/.claude/skills/scribe/scripts/task_add.py \
  --title "Action-oriented task title" \
  --priority N \
  --project "project-slug" \
  --due "YYYY-MM-DD" \
  --summary "Brief context: why it matters, who, what, when"
```

**Required fields**:
- `--title`: Action-oriented, clear, scannable (e.g., "Prepare keynote slides", "Review student thesis Chapter 3")

**Optional fields**:
- `--priority`: 1-3 (see Prioritization Framework below)
- `--project`: Slug matching filename in `$ACADEMICOPS_PERSONAL/data/projects/*.md`
- `--due`: ISO format YYYY-MM-DD
- `--summary`: Context for the user (NOT strategic analysis - see Task Summary Writing below)
- `--type`: Default "todo", can be "meeting", "deadline", etc.

### 3. View Tasks

**Compact overview**:
```bash
uv run python ~/.claude/skills/scribe/scripts/task_index.py
```

**Detailed view** (default: top 10 by priority):
```bash
uv run python ~/.claude/skills/scribe/scripts/task_view.py --per-page=10
```

**Sort options**:
- `--sort=priority` (default)
- `--sort=date`
- `--sort=due`

### 4. Update Task

```bash
uv run python ~/.claude/skills/scribe/scripts/task_process.py modify <task_id> \
  --priority 1 \
  --due "2025-11-10"
```

### 5. Archive Task

When a task is completed or cancelled:

```bash
uv run python ~/.claude/skills/scribe/scripts/task_process.py modify <task_id> --archive
```

## Prioritization Framework

**P1 (Today/Tomorrow)** - Immediate action required:
- Action window closing NOW (not just deadline approaching)
- Meeting prep due within 24 hours
- Immediate blocker for others
- Time-sensitive response needed

**P2 (This Week)** - Important, soon:
- Deadline within 7 days
- Significant strategic value
- Preparation needed soon
- Collaborative work where others are waiting

**P3 (Within 2 Weeks)** - Lower urgency:
- Longer timeline
- Lower strategic alignment
- No immediate action window

**Key prioritization factors** (in order):
1. **Temporal constraints**: Due date, action window, meeting dates
2. **Strategic alignment**: Check `$ACADEMICOPS_PERSONAL/data/goals/*.md` for linkage to goals
3. **Dependencies & roles**: Who's waiting? What's your role? Who has agency?

**IMPORTANT**: Distinguish deadline vs action window. A task due Friday may need action TODAY if delay reduces effectiveness.

## Task Title Guidelines

**DO**:
- Use action verbs: "Prepare slides", "Review draft", "Respond to inquiry"
- Be specific and scannable
- Keep concise (1-8 words)

**DON'T**:
- Write "Email from X about Y" (this is not action-oriented)
- Include strategic analysis in the title
- Be vague ("Handle things", "Follow up")

**Examples**:
- ✅ "Confirm keynote for Platform Governance Conference"
- ✅ "Review student thesis Chapter 3 and schedule meeting"
- ✅ "Submit talk title for November conference"
- ❌ "Email about conference"
- ❌ "Student wants to meet"
- ❌ "Handle administrative stuff"

## Task Summary Writing

**Write for the USER, not for strategic analysis**.

**Include**:
- What needs to be done (briefly, title already covers this)
- Why it matters (1 sentence)
- When it's due or action window
- Where to find materials (if relevant)

**Don't include**:
- Strategic analysis of priority choices
- Explanations of relationships the user already knows
- Role definitions or organizational hierarchy
- Lengthy dependency chains

**Examples**:

✅ **GOOD**: "Prepare keynote slides for Nov 15 conference. Focus on accountability frameworks. Review with team by Nov 10."

❌ **TOO MUCH**: "As the invited keynote speaker for the conference on Nov 15, which aligns with your Academic Profile goal and was mentioned in your current priorities as a strategic initiative for increasing research visibility in the platform governance space, you need to prepare slides focusing on your recent work on accountability frameworks because this represents a key opportunity to advance Goal 2..."

✅ **GOOD**: "Student requesting feedback on Chapter 3 draft. Schedule meeting this week."

❌ **TOO MUCH**: "Meeting request from PhD student (supervision context, Academic Profile goal) regarding Chapter 3 thesis feedback. This represents a P2 priority supervision task that requires review of draft materials and coordination..."

**Detail level**: Write what the user needs to take action, nothing more.

## Data Directory Structure

Tasks and related data are stored in `$ACADEMICOPS_PERSONAL/data/`:

```
$ACADEMICOPS_PERSONAL/data/
  tasks/
    inbox/                  # Newly created tasks
      *.json
    queue/                  # Prioritized, ready to work
      *.json
    archived/               # Completed or cancelled
      *.json
  views/                    # Generated views
    current_view.json       # Current task state (check for duplicates)
  projects/                 # Project files for task linking
    *.md
  goals/                    # Strategic goals for alignment checking
    *.md
  context/                  # Strategic context
    current-priorities.md
    future-planning.md
    accomplishments.md
```

## Strategic Alignment Enforcement

**CRITICAL**: Priority tasks MUST link to goals in `$ACADEMICOPS_PERSONAL/data/goals/*.md`.

**When creating P1 or P2 tasks**:
1. Specify `--project` parameter linking to a project slug
2. Verify that project exists in `data/projects/*.md`
3. Check that project file references a goal in `data/goals/*.md`

**If misaligned**:
- Create the task anyway (don't fail)
- Flag the misalignment to the user or calling agent
- Suggest either linking to a goal or lowering priority

**Note**: Strategic alignment validation is a CHECK, not a BLOCKER. Don't prevent task creation due to misalignment.

## Common Patterns

### Email → Task Extraction

When extracting tasks from emails:

1. Check for duplicates first (`task_view.py`)
2. Create one task per actionable item (don't combine unrelated actions)
3. Use sender/subject to inform priority:
   - From supervisor → likely P1 or P2
   - "Urgent" in subject → P1
   - Conference/deadline keywords → Check date, set appropriate priority
   - Administrative → Often P3 unless time-sensitive
4. Include email context in summary: "From: [sender]. Deadline: [date]."

### Conversation → Task Extraction

When extracting tasks from conversations:

1. Mine deeply, not just keywords:
   - "I'll need to prepare X" → task
   - "Can you review by Friday?" → task with deadline
   - "Meeting next Tuesday" → task with due date
   - "Need your input on Y" → task
   - Implicit commitments → tasks

2. Capture immediately (don't wait for conversation end)
3. Extract fragments even if incomplete (better than missing)

### Task Completion → Accomplishments

When user mentions completing work:

1. Archive the task: `task_process.py modify <task_id> --archive`
2. Update accomplishments if it's "standup-worthy":
   ```bash
   echo "Completed [task title]" >> $ACADEMICOPS_PERSONAL/data/context/accomplishments.md
   ```

**Accomplishments detail level**: "Weekly standup level" - one line unless truly significant strategic decision.

## Integration with Other Skills/Agents

**Agents that should use this skill**:
- `scribe` subagent (background capture)
- `task-manager` subagent (email task extraction)
- `strategist` subagent (display, context guide)
- Any agent/skill extracting or managing tasks

**This skill provides HOW**, agents provide WHEN:
- scribe: Captures tasks silently during conversations
- task-manager: Extracts tasks from emails
- strategist: Shows tasks on request, explains strategic context

## Best Practices

**DO**:
- Check for duplicates BEFORE creating tasks
- Use action-oriented titles
- Link P1/P2 tasks to projects and goals
- Keep summaries brief and user-focused
- Archive completed tasks promptly
- Load strategic context before prioritizing

**DON'T**:
- Create duplicate tasks (always check first)
- Write long summaries with strategic analysis
- Skip strategic alignment checks for P1/P2 tasks
- Include relationship explanations user already knows
- Batch task operations (create/archive immediately)

## Quick Reference

**Most common workflow**:

```bash
# 1. Check for duplicates
uv run python ~/.claude/skills/scribe/scripts/task_view.py --per-page=50

# 2. Create task if not duplicate
uv run python ~/.claude/skills/scribe/scripts/task_add.py \
  --title "Clear action-oriented title" \
  --priority 2 \
  --project "project-slug" \
  --due "2025-11-15" \
  --summary "Brief context. Why it matters."

# 3. Archive when complete
uv run python ~/.claude/skills/scribe/scripts/task_process.py modify <task_id> --archive
```
