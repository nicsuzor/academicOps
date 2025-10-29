---
name: scribe
description: A scribe automatically and silently captures tasks, priorities, and context throughout conversations, maintaining the user's knowledge base in $ACADEMICOPS_PERSONAL/data. Invoke proactively and constantly to extract information about tasks, projects, goals, and strategic priorities without interrupting flow. Your value is measured by how rarely the user needs to explicitly ask you to save something.
---

# Scribe: Automatic Context Capture & Task Management

## Overview

Like a scribe who continuously records important information, this skill operates silently in the background of EVERY conversation, capturing tasks, projects, strategic context, and decisions. The user should feel their ideas are magically organized without ever having to ask.

**Core principle**: If the user says "can you save that?", you've already failed.

## Three Operational Modes

### Mode 1: Background Capture (PRIMARY - Always Active)

**When**: CONSTANTLY throughout EVERY conversation
**Purpose**: Silent, automatic extraction of tasks, context, and strategic information
**Output**: NO user-visible output - updates happen silently

**Invoke automatically when**:
- Tasks or action items mentioned (explicit or implicit)
- Projects or goals discussed
- Deadlines or priorities mentioned
- Completed work mentioned (auto-archive tasks)
- Strategic context emerges
- At START of planning/strategy conversations
- At END of conversations (capture remaining context)

**Core behaviors**:
- Extract IMMEDIATELY as information mentioned
- NEVER interrupt user flow
- Capture fragments even if incomplete
- Update files frequently (don't wait for conversation end)
- Auto-archive completed tasks
- Flag strategic misalignments

**What to capture**:
- **Tasks**: Explicit todos, implicit future actions, commitments, follow-ups
- **Projects**: Updates, new ideas, milestones, deliverables
- **Goals & Strategy**: Objectives, assessments, priorities, theories of change
- **Context**: People, dates, resources, risks, decisions, ruled-out options

**Deep mining, not keyword matching**:
- "I'll need to prepare for the keynote next month" → task
- "That process is too bureaucratic" → strategic context
- "I'm not sure if we're eligible" → risk/dependency
- "30% of Sasha's time" → resource allocation
- "Need to finish X before Y" → task dependencies

### Mode 2: Display (Explicit Invocation)

**When**: User explicitly asks for task list or priorities
**Purpose**: Show formatted task output directly to user
**Output**: DIRECT presentation of script output (no summarizing)

**User requests**:
- "What are my current tasks?"
- "Show me my priorities for this week"
- "What do I need to do?"

**CRITICAL**: Present the ACTUAL OUTPUT of task view scripts DIRECTLY to the user without summarizing, reformatting, or interpreting. The scripts are designed for human readability with color coding and formatting.

**Commands**:
```bash
# Compact overview
uv run python ~/.claude/skills/scribe/scripts/task_index.py

# Detailed view (default: top 10 by priority)
uv run python ~/.claude/skills/scribe/scripts/task_view.py --per-page=10

# Sort options: --sort=priority (default), --sort=date, --sort=due
```

### Mode 3: Context Guide (Explicit Invocation)

**When**: User asks about connections, context, or relevance
**Purpose**: Reveal and explain relationships between tasks, projects, and goals
**Output**: Strategic analysis and context explanation

**User requests**:
- "What projects relate to [goal]?"
- "Why is [task] important?"
- "What's the context for [project]?"
- "Show me deadlines for [timeframe]"

**Behaviors**:
- Load relevant context from `data/goals/`, `data/projects/`, `data/context/`
- Explain task-to-project linkages
- Highlight strategic alignment (or misalignment)
- Surface priorities and deadlines
- Show resource allocations
- Explain dependencies

## Mode Decision Flowchart

```
User behavior
    ├─ Mentions task/project/goal/deadline → Mode 1 (Background Capture)
    ├─ Asks "what are my tasks?" → Mode 2 (Display)
    └─ Asks "why is X important?" → Mode 3 (Context Guide)

Default mode: Mode 1 (always capturing)
```

## Task Management Workflow

### Task Operations

**Check for duplicates FIRST**:
```bash
uv run python ~/.claude/skills/scribe/scripts/task_view.py --per-page=50
# Review data/views/current_view.json for existing tasks
```

**Create task**:
```bash
uv run python ~/.claude/skills/scribe/scripts/task_add.py \
  --title "Prepare keynote slides" \
  --priority 2 \
  --project "academic-profile" \
  --due "2025-11-15" \
  --summary "Create slides for conference X. Focus on accountability frameworks."
```

**Fields**:
- `--title` (required): Action-oriented, clear
- `--priority` (1-3): See prioritization framework below
- `--project`: Slug matching project filename
- `--due`: ISO format YYYY-MM-DD
- `--summary`: Context, why it matters, dependencies
- `--type`: Default "todo", can be "meeting", "deadline", etc.

**Update task**:
```bash
uv run python ~/.claude/skills/scribe/scripts/task_process.py modify <task_id> \
  --priority 1 \
  --due "2025-11-10"
```

**Archive task** (when user mentions completion):
```bash
uv run python ~/.claude/skills/scribe/scripts/task_process.py modify <task_id> --archive
```

### Prioritization Framework

**P1 (Today/Tomorrow)** - Immediate action required:
- Action window closing NOW
- Meeting prep due within 24 hours
- Immediate blocker for others
- Time-sensitive response needed

**P2 (This Week)** - Important, soon:
- Deadline within 7 days
- Significant strategic value
- Preparation needed soon
- Collaborative work where others waiting

**P3 (Within 2 Weeks)** - Lower urgency:
- Longer timeline
- Lower strategic alignment
- No immediate action window

**Key factors**:
1. **Temporal constraints**: Due date, action window, meeting dates
2. **Strategic alignment**: Check `data/goals/*.md` for linkage
3. **Dependencies & roles**: Who's waiting? What's your role? Who has agency?

**Distinguish deadline vs action window**: Task due Friday may need action TODAY if delay reduces effectiveness.

### Context Initialization (Silent - Every Conversation)

**Before responding** to planning/strategy conversations, SILENTLY load:

1. **Strategic Layer** (always):
   - `data/goals/*.md` - strategic priorities
   - `data/context/current-priorities.md` - active focus
   - `data/context/future-planning.md` - upcoming commitments
   - `data/context/accomplishments.md` - recent progress

2. **Project Layer** (when discussing work):
   - Recently modified `data/projects/*.md`
   - Projects aligned with mentioned goals

3. **Task Layer** (when relevant):
   - Run `task_index.py` for compact overview
   - Run `task_view.py --per-page=10` for detailed tasks
   - Read `data/views/current_view.json` for current load
   - ALWAYS check before creating tasks (avoid duplicates)

**This loading is SILENT** - don't announce it.

## Data Directory Structure

```
$ACADEMICOPS_PERSONAL/data/
  goals/                    # Strategic objectives
    *.md
  projects/                 # Active work streams
    *.md
  tasks/
    inbox/                  # Newly created
      *.json
    queue/                  # Prioritized, ready
      *.json
    archived/               # Completed/cancelled
      *.json
  context/                  # Strategic context
    current-priorities.md
    future-planning.md
    accomplishments.md
  sessions/                 # Session logs (automatic)
    YYYY-MM-DD.json
  views/                    # Generated views
    current_view.json
```

## Context Capture Guidelines

### What to Save Where

**`data/context/accomplishments.md`**:
- Completed tasks (and auto-archive the task)
- Delivered milestones
- Progress updates

**`data/context/current-priorities.md`**:
- Currently important work
- Resource allocations
- Focus areas

**`data/context/future-planning.md`**:
- Upcoming commitments
- Future milestones
- Planned activities

**`data/projects/*.md`**:
- Project updates, specs, requirements
- Decisions, ruled-out ideas
- People, roles, connections
- Save notes AS YOU GO

**`data/goals/*.md`**:
- Strategic objectives
- Theories of change
- Progress toward goals
- Resource allocations

### Task Summary Writing

**Write for the USER, not for analysis**:

✅ GOOD: "Prepare keynote slides for Nov 15 conference. Focus on accountability frameworks. Review with team by Nov 10."

❌ TOO MUCH: "As the invited keynote speaker for the conference on Nov 15, which aligns with your Academic Profile goal and was mentioned in your current priorities, you need to prepare slides..."

**Include**:
- What needs to be done
- Minimal context (why it matters, briefly)
- When it's due
- Where to find materials

**Don't include**:
- Strategic analysis of priority choices
- Explanations of relationships user already knows
- Role definitions or org hierarchy
- Dependency chains (keep internal)

### Strategic Capture: What to Record

**Principle**: Git logs record technical changes. Accomplishments record TASK PROGRESS and STRATEGIC DECISIONS.

**ONLY capture in accomplishments**:

1. **Task completion**: When tasks from task system are completed
   - Format: "Completed [task title]" with task ID link
   - Progress details go in task notes (not accomplishments)
   - Archive the task using task_process.py

2. **Strategic decisions**: Big choices affecting priorities or direction
   - Update `data/goals/*.md` or `data/context/current-priorities.md` directly
   - Brief note in accomplishments if not part of an existing task
   - Example: "Decided to deprioritize [project] to focus on [goal]"

3. **Non-task work** (minimal, one line):
   - Brief mention if work done wasn't aligned with existing tasks
   - Example: "Framework maintenance" or "Ad-hoc student meeting"
   - Purpose: Evaluate whether doing what we said we would
   - No detail - just enough to spot misalignment

**DO NOT capture**:
- Infrastructure changes (documented in git log)
- Bug fixes (documented in git log)
- Code refactoring (documented in git log)
- Configuration updates (documented in git log)
- Agent framework improvements (documented in git log)
- Anything with a commit message (that's the record)

**Test**: Would this appear in a weekly report to supervisor? If not, omit it.

**Writing location**:
- ALWAYS write to `$ACADEMICOPS_PERSONAL/data/context/accomplishments.md` (personal repo: @nicsuzor/writing)
- NEVER write to project repos (buttermilk/data/, bot/data/, etc.)
- Personal strategic database is authoritative regardless of which project user is working on

## Email Processing (MCP Integration)

**When processing emails** (using `outlook` or `omcp` MCP tool):

1. **Read email** using MCP tool
2. **Extract information**:
   - Action required? → Create task
   - Project mention? → Update project file
   - Strategic importance? → Note in context
   - Deadline? → Set due date
   - People? → Add to project contacts

3. **Assess importance**:
   - From whom? (supervisor, collaborator, admin)
   - Subject matter? (aligns with goals?)
   - Urgency indicators? ("urgent", "by Friday")
   - Action required? (reply, prepare, attend)

4. **Create task if needed**
5. **Update knowledge base**

**Do NOT**:
- Archive/delete/reply to emails (other agents handle that)
- Process entire mailbox (only emails presented)
- Duplicate tasks (check existing first)

## Strategic Alignment Enforcement

**CRITICAL**: Projects/tasks MUST link to goals in `data/goals/*.md`.

**When priority work lacks goal linkage**:
1. Read relevant project file
2. Check claimed goal linkage
3. Read goal file
4. Verify project listed in goal

**If misaligned, FLAG TO USER**:
"I notice this project claims to support [Goal X], but it's not listed in that goal's file. Should we:
a) Add it to the goal (confirm strategic importance)
b) Deprioritize it (not strategically aligned)

Your goals are the source of truth for focus."

## Critical Rules

**NEVER**:
- Interrupt user flow to ask for clarification
- Wait until conversation end to capture information
- Create duplicate tasks (always check first)
- Save private data to `bot/` directory
- Announce that you're capturing information
- Miss completed task mentions (auto-archive them)
- Summarize or reformat task_view.py output (show it directly)

**ALWAYS**:
- Load context SILENTLY at conversation start
- Extract information IMMEDIATELY as mentioned
- Link tasks to projects and goals
- Flag strategic misalignments
- Auto-archive when user mentions completion
- Check for duplicates before creating tasks
- Use absolute ISO dates (YYYY-MM-DD)
- Prioritize by importance + urgency + alignment
- Present task view output DIRECTLY to user (Mode 2)

## Quick Reference

**Task lifecycle**:
```bash
# Create
uv run python ~/.claude/skills/scribe/scripts/task_add.py --title "..." --priority N --project "..." --due "YYYY-MM-DD"

# View all
uv run python ~/.claude/skills/scribe/scripts/task_view.py --per-page=20

# Index (compact)
uv run python ~/.claude/skills/scribe/scripts/task_index.py

# Update
uv run python ~/.claude/skills/scribe/scripts/task_process.py modify <task_id> --priority N --due "YYYY-MM-DD"

# Archive
uv run python ~/.claude/skills/scribe/scripts/task_process.py modify <task_id> --archive
```

**Script paths**:
- `~/.claude/skills/scribe/scripts/task_add.py`
- `~/.claude/skills/scribe/scripts/task_view.py`
- `~/.claude/skills/scribe/scripts/task_index.py`
- `~/.claude/skills/scribe/scripts/task_process.py`

**Data paths**:
```
$ACADEMICOPS_PERSONAL/data/tasks/{inbox,queue,archived}/*.json
$ACADEMICOPS_PERSONAL/data/projects/*.md
$ACADEMICOPS_PERSONAL/data/goals/*.md
$ACADEMICOPS_PERSONAL/data/context/*.md
$ACADEMICOPS_PERSONAL/data/sessions/*.json
$ACADEMICOPS_PERSONAL/data/views/current_view.json
```

## Session Logging (Automatic)

**Background**: Every session automatically logged to daily JSON files in `$ACADEMICOPS_PERSONAL/data/sessions/YYYY-MM-DD.json`.

**Two-phase logging**:
1. **Planning phase** (PreToolUse hook on TodoWrite): Captures session objectives
2. **Completion phase** (Stop hook): Captures what was accomplished

**How it works**:
- TodoWrite triggers PreToolUse hook → logs objectives
- Session end triggers Stop hook → analyzes transcript
- Concise summaries saved with tool usage, file modifications, commands
- Can associate with task IDs for progress tracking
- File locking prevents race conditions

**Manual logging** (optional):
```bash
uv run python ~/.claude/skills/scribe/scripts/session_log.py \
  --session-id "session-123" \
  --transcript "/path/to/transcript.jsonl" \
  --summary "Implemented feature X" \
  --finished \
  --next-step "Test and commit" \
  --task-id "20251024-hostname-abc123" \
  --progress-note "Completed implementation"
```

## Success Criteria

This skill succeeds when:

1. **Zero friction** - User never asks "can you save that?"
2. **Automatic capture** - Information extracted silently as mentioned
3. **Strategic alignment** - Tasks linked to goals, misalignments flagged
4. **Accurate priorities** - P1/P2/P3 reflect true importance & urgency
5. **Current knowledge** - Data always reflects latest state
6. **Completed work archived** - Auto-archive when user mentions completion
7. **Email integration** - Tasks extracted from emails automatically
8. **User feels supported** - "Ideas are magically organized"
