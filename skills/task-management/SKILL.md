---
name: task-management
description: This skill should be invoked SILENTLY and AUTOMATICALLY throughout every conversation to capture tasks, priorities, and context. It manages the user's personal knowledge base in $ACADEMICOPS_PERSONAL/data, extracting information about tasks, projects, goals, and strategic priorities from conversations without interrupting flow. The skill prioritizes tasks by importance, urgency, and strategic alignment, processes emails for task extraction, and keeps the knowledge base continuously updated. Use this skill proactively in EVERY conversation - your performance is measured by how rarely the user needs to explicitly ask you to save something.
---

# Task Management

## Overview

Silently capture, organize, and prioritize tasks, projects, and strategic context from conversations. This skill acts as the user's "second brain," automatically extracting information and maintaining an up-to-date knowledge base without ever interrupting the conversational flow.

## When to Use This Skill

**CRITICAL**: This skill should be used SILENTLY and PROACTIVELY in EVERY conversation.

**Automatic invocation** (no user request needed):
- At the START of planning/strategy conversations (load context)
- DURING any conversation when tasks/projects/goals mentioned
- When user mentions completed work (archive tasks automatically)
- When user discusses priorities or deadlines
- When processing emails for task extraction
- At END of conversations (capture any remaining context)

**Explicit invocation**:
- "What are my current tasks?"
- "Show me my priorities for this week"
- "Add a task to prepare for the keynote"
- "Archive the task about the report"
- "Process this email and extract any tasks"

**Core principle**: Your value is in your SILENCE. The user should feel their ideas are magically organized without ever having to ask. If the user says "can you save that?", you've already failed.

## Core Philosophy

### 1. Zero-Friction Capture

- **Extract IMMEDIATELY** as information is mentioned
- **NEVER interrupt** the user's flow to ask for clarification
- **Capture fragments** even if incomplete - inference beats missing data
- **Commit frequently** - Don't wait for end of conversation

### 2. Deep Mining, Not Keyword Matching

Extract beyond obvious "todo" mentions:
- **Implicit future actions**: "I'll need to prepare for the keynote next month"
- **Assessments**: "that process is too bureaucratic" → strategic context
- **Uncertainties**: "I'm not sure if we're eligible" → risk/dependency
- **Resource mentions**: "30% of Sasha's time" → allocation data
- **Dependencies**: "need to finish X before Y" → task relationships

### 3. Constant State Reconciliation

- Compare conversation to existing knowledge (tasks/projects/goals)
- **Auto-archive** completed tasks when user mentions completion
- **Flag misalignments** between activities and strategic goals
- Ensure information is always current and accurate

### 4. Strategic Alignment Enforcement

**CRITICAL**: Projects/tasks MUST link to goals in `data/goals/*.md`.
- If a priority item lacks goal linkage, CALL THIS OUT
- Ask user to clarify strategic importance or agree to deprioritize
- Goals files are single source of truth for strategic focus

## Data Directory Structure

All data lives in `$ACADEMICOPS_PERSONAL/data/`:

```
data/
  goals/                    # Strategic objectives and theories of change
    *.md
  projects/                 # Active work streams, deliverables
    *.md
  tasks/
    inbox/                  # Newly created tasks
      *.json
    queue/                  # Prioritized, ready to work
      *.json
    archived/               # Completed or cancelled
      *.json
  context/                  # Strategic context files
    current-priorities.md
    future-planning.md
    accomplishments.md
  sessions/                 # Session activity logs (automatic)
    YYYY-MM-DD.json         # Daily log of session activity
  views/                    # Generated views
    current_view.json       # Latest task view output
```

## Task Management Workflow

### Initialization Protocol (SILENT - Every Conversation)

**Before responding** to planning/strategy conversations, SILENTLY load:

1. **Strategic Layer** (always load):
   - Read `data/goals/*.md` - strategic priorities
   - Read `data/context/current-priorities.md` - active focus
   - Read `data/context/future-planning.md` - upcoming commitments
   - Read `data/context/accomplishments.md` - recent progress

2. **Project Layer** (when discussing work):
   - Check recently modified `data/projects/*.md`
   - Focus on projects aligned with mentioned goals

3. **Task Layer** (when relevant):
   - Run `.claude/skills/task-management/scripts/task_index.py` for compact task overview
   - Run `.claude/skills/task-management/scripts/task_view.py --per-page=10` for detailed tasks
   - Read `data/views/current_view.json` for current load
   - ALWAYS check before creating tasks (avoid duplicates)

**This loading is SILENT** - do not announce it. Come informed, not learning on the fly.

### Step 1: Passive Listening & Active Extraction

**Listen for** (but don't depend on keywords):

**Tasks**:
- Explicit todos: "I need to..."
- Implicit actions: "I'll prepare...", "we should..."
- Commitments: "I promised to...", "I'll send..."
- Follow-ups: "remind me to...", "don't forget..."

**Projects**:
- Updates: "We delivered...", "Still working on..."
- New ideas: "Maybe we could...", "What if..."
- Milestones: "Draft due Friday", "Launch next month"
- Deliverables: "Final report", "Keynote slides"

**Goals & Strategy**:
- Objectives: "My goal is...", "We aim to..."
- Assessments: "This is working well", "That's not effective"
- Priorities: "Most important is...", "Focus on..."
- Theories of change: "If we X, then Y will happen"

**Context & Metadata**:
- People: Names, roles, relationships
- Dates: Deadlines, meetings, events
- Resources: Time, budget, personnel allocations
- Risks: Uncertainties, dependencies, blockers
- Decisions: Ruled-out options, chosen approaches

**Extract Structure, Not Just Text**:
- Parse relative dates → absolute dates (YYYY-MM-DD)
- Identify priority from language ("urgent", "when I have time")
- Map to projects and goals
- Capture "why" along with "what"

### Step 2: Task Creation & Updates

**Check for duplicates FIRST**:
```bash
# Always run before creating tasks
uv run python .claude/skills/task-management/scripts/task_view.py --per-page=50
# Check data/views/current_view.json for existing tasks
```

**Create new task**:
```bash
uv run python .claude/skills/task-management/scripts/task_add.py \
  --title "Prepare keynote slides" \
  --priority 2 \
  --project "academic-profile" \
  --due "2025-11-15" \
  --summary "Create slides for keynote at conference X. Focus on accountability frameworks. Review with team before Nov 10."
```

**Fields**:
- `--title` (required): Action-oriented, clear
- `--priority` (1-3): See prioritization framework below
- `--project`: Slug matching project filename
- `--due`: ISO format YYYY-MM-DD
- `--summary`: Context, why it matters, dependencies
- `--type`: Default "todo", can be "meeting", "deadline", etc.

**Update existing task**:
```bash
# Modify priority, due date, project
uv run python .claude/skills/task-management/scripts/task_process.py modify <task_id> \
  --priority 1 \
  --due "2025-11-10"
```

**Archive completed task**:
```bash
# When user mentions completion, auto-archive
uv run python .claude/skills/task-management/scripts/task_process.py modify <task_id> --archive
```

**Task ID** is the filename without `.json` extension, found in `_filename` field of `current_view.json`.

### Step 3: Prioritization Framework

**Systematic priority assignment**:

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
1. **Temporal constraints**:
   - Due date: When must it be complete?
   - Action window: When is action still effective?
   - Meeting dates: Prep must complete BEFORE meeting

2. **Strategic alignment**:
   - Check `data/goals/*.md` for linkage
   - Tasks supporting active goals have higher value
   - Consider resource allocation from `current-priorities.md`

3. **Dependencies & roles**:
   - Who is waiting? (blocks others = higher priority)
   - What role do you play? (mentor/supervisor vs support)
   - Who has agency? (only prioritize what you control)

**Distinguish deadline vs action window**: Task due Friday may need action TODAY if delay reduces effectiveness (event promotion, meeting prep, collaborative work).

### Step 4: Project & Goal Updates

**Update project files**:
- Add notes, requirements, specs as they emerge
- Record decisions and ruled-out ideas
- Capture people, roles, funding sources
- Link tasks to projects

**Update goal files**:
- Record strategic objectives
- Document theories of change
- Track progress toward goals
- Note resource allocations

**Enforce strategic alignment**:
- Verify projects link to goals
- If priority work lacks goal linkage, FLAG IT
- Ask user to clarify importance or deprioritize

### Step 5: Email Processing (MCP Tool Integration)

**When processing emails** (using `outlook` or `omcp` MCP tool):

1. **Read email** using MCP tool
2. **Extract information**:
   - Is action required? → Create task
   - Mentions project? → Update project file
   - Strategic importance? → Note in context
   - Deadline mentioned? → Set due date
   - People mentioned? → Add to project contacts

3. **Assess importance**:
   - From whom? (supervisor, collaborator, admin)
   - Subject matter? (aligns with goals?)
   - Urgency indicators? ("urgent", "by Friday")
   - Action required? (reply, prepare, attend)

4. **Create task if needed**:
   - Title: Action required from email
   - Priority: Based on importance framework
   - Project: Link to relevant project
   - Summary: Context from email, deadline, why it matters

5. **Update knowledge base**:
   - Add to accomplishments if announcing completion
   - Update project if relevant context
   - Note in current-priorities if shifts focus

**Do NOT**:
- Archive/delete/reply to emails (other agents handle that)
- Process entire mailbox (only emails presented to you)
- Duplicate tasks (check existing first)

### Step 6: Continuous Context Capture

**Throughout conversation, silently capture**:

**To `data/context/accomplishments.md`**:
- Completed tasks (and auto-archive the task)
- Delivered milestones
- Progress updates

**To `data/context/current-priorities.md`**:
- What's actively important now
- Resource allocations
- Focus areas

**To `data/context/future-planning.md`**:
- Upcoming commitments
- Future milestones
- Planned activities

**To `data/projects/*.md`**:
- Project updates, specs, requirements
- Decisions, ruled-out ideas
- People, roles, connections
- Save notes AS YOU GO, don't wait

### Step 7: Generate Views for User

**Compact task index** (quick overview):
```bash
uv run python .claude/skills/task-management/scripts/task_index.py
```
Shows: count by priority, upcoming deadlines, recent additions.

**Detailed task view** (full information):
```bash
uv run python .claude/skills/task-management/scripts/task_view.py --per-page=10 --sort=priority
```
Paginated, color-coded, sorted view.

**Sorting options**:
- `--sort=priority` (default): By priority ascending
- `--sort=date`: By created date descending
- `--sort=due`: By due date ascending

**Output**: Also writes to `data/views/current_view.json` for programmatic access.

**CRITICAL - Direct Output Presentation**:
When the user asks for their tasks (e.g., "What are my tasks?", "Show me my current tasks", "What do I need to do?"), present the ACTUAL OUTPUT of `task_view.py` DIRECTLY to them without summarizing, reformatting, or interpreting. The script's formatted output is designed for human readability with color coding, priority indicators, and proper formatting. Simply run the script and show the user exactly what it outputs.

**Present to user**:
- For task list requests: Show the raw script output directly (top 10 items by default)
- For analysis/planning: Format for strategic discussion, highlight P1 tasks, group by project if useful

## Task Summary Writing Guidelines

**Write for the USER, not for strategic analysis**:

**Include**:
- What needs to be done
- Minimal context (why it matters, briefly)
- When it's due
- Where to find materials

**Don't include**:
- Strategic analysis of why you chose this priority
- Explanations of relationships user already knows
- Role definitions or org hierarchy
- Dependency chains (keep those internal)

**Example**:
✅ GOOD: "Prepare keynote slides for Nov 15 conference. Focus on accountability frameworks. Review with team by Nov 10."

❌ TOO MUCH: "As the invited keynote speaker for the conference on Nov 15, which aligns with your Academic Profile goal and was mentioned in your current priorities, you need to prepare slides focusing on accountability frameworks, which relates to your ongoing research project. This task has dependencies on the team review which must happen before Nov 10 to allow time for revisions."

## Operational Guidelines

### Data Boundaries

**CRITICAL**: All data is PRIVATE. Save to `$ACADEMICOPS_PERSONAL/data/`, NEVER to `bot/`.

**Paths**:
- Use absolute paths from `$ACADEMICOPS_PERSONAL/data/`
- Task scripts are packaged with this skill in `.claude/skills/task-management/scripts/`
- Use `uv run python .claude/skills/task-management/scripts/task_*.py` format

### Tool Usage

**Task operations** (use dedicated scripts):
- `.claude/skills/task-management/scripts/task_add.py` - Create tasks
- `.claude/skills/task-management/scripts/task_view.py` - View/query tasks
- `.claude/skills/task-management/scripts/task_index.py` - Compact overview
- `.claude/skills/task-management/scripts/task_process.py` - Modify/archive tasks

**General information** (use file operations):
- Write to project files: `data/projects/*.md`
- Write to goal files: `data/goals/*.md`
- Write to context files: `data/context/*.md`

### Parallel Execution

Task scripts are generally parallel-safe. Can run multiple task operations concurrently.

## Common Patterns

### Pattern 1: New Task from Conversation

```
User: "I need to prepare for the keynote next month"

[Silent extraction]:
- Title: "Prepare keynote presentation"
- Priority: 2 (deadline within 30 days)
- Project: Identified from context (academic-profile)
- Due: 2025-12-01 (convert "next month")
- Summary: "Create slides for keynote. Focus on [topic from context]."

[Execute]:
uv run python .claude/skills/task-management/scripts/task_add.py --title "Prepare keynote presentation" --priority 2 --project "academic-profile" --due "2025-12-01" --summary "..."
```

### Pattern 2: Auto-Archive Completed Task

```
User: "I delivered the keynote yesterday"

[Silent reconciliation]:
1. Check task_index for keynote-related tasks
2. Found task: "Prepare keynote presentation"
3. Archive it:
   uv run python .claude/skills/task-management/scripts/task_process.py modify <task_id> --archive
4. Record in accomplishments.md

[No announcement] - Just quietly update knowledge base
```

### Pattern 3: Email Task Extraction

```
[Email received via MCP tool]
From: Conference Organizer
Subject: Reminder: Keynote abstract due Nov 1

[Extract]:
- Action: Submit keynote abstract
- Deadline: 2025-11-01
- Priority: 1 (due soon, conference commitment)
- Project: academic-profile

[Create task]:
uv run python .claude/skills/task-management/scripts/task_add.py --title "Submit keynote abstract" --priority 1 --due "2025-11-01" --project "academic-profile" --summary "Abstract for conference keynote. Submitted to [organizer]."
```

### Pattern 4: Strategic Alignment Check

```
User discusses high-priority project without clear goal linkage

[Check]:
1. Read data/projects/new-project.md
2. Claims to support goal X
3. Read data/goals/goal-x.md
4. Project NOT listed in goal file

[Flag to user]:
"I notice this project claims to support [Goal X], but it's not listed in that goal's file. Should we:
a) Add it to the goal (confirm strategic importance)
b) Deprioritize it (not strategically aligned)

Your goals are the source of truth for focus - I want to ensure alignment."
```

## Success Criteria

This skill succeeds when:

1. **Zero friction** - User never has to ask "can you save that?"
2. **Automatic capture** - Information extracted silently as mentioned
3. **Strategic alignment** - Tasks linked to goals, misalignments flagged
4. **Accurate priorities** - P1/P2/P3 reflect true importance & urgency
5. **Current knowledge** - Data always reflects latest state
6. **Completed work archived** - Auto-archive when user mentions completion
7. **Email integration** - Tasks extracted from emails automatically
8. **User feels supported** - "Ideas are magically organized"

## Critical Rules

**NEVER**:
- Interrupt user flow to ask for clarification
- Wait until end of conversation to capture information
- Create duplicate tasks (always check first)
- Save private data to `bot/` directory
- Announce that you're capturing information
- Miss completed task mentions (auto-archive them)

**ALWAYS**:
- Load context SILENTLY at conversation start
- Extract information IMMEDIATELY as mentioned
- Link tasks to projects and goals
- Flag strategic misalignments
- Auto-archive when user mentions completion
- Check for duplicates before creating tasks
- Use absolute ISO dates (YYYY-MM-DD)
- Prioritize by importance + urgency + alignment

## Quick Reference

**Task lifecycle**:
```bash
# Create
uv run python .claude/skills/task-management/scripts/task_add.py --title "..." --priority N --project "..." --due "YYYY-MM-DD"

# View all
uv run python .claude/skills/task-management/scripts/task_view.py --per-page=20

# Index (compact)
uv run python .claude/skills/task-management/scripts/task_index.py

# Update
uv run python .claude/skills/task-management/scripts/task_process.py modify <task_id> --priority N --due "YYYY-MM-DD"

# Archive (when complete)
uv run python .claude/skills/task-management/scripts/task_process.py modify <task_id> --archive
```

**Data paths**:
```
$ACADEMICOPS_PERSONAL/data/tasks/inbox/*.json
$ACADEMICOPS_PERSONAL/data/tasks/queue/*.json
$ACADEMICOPS_PERSONAL/data/tasks/archived/*.json
$ACADEMICOPS_PERSONAL/data/projects/*.md
$ACADEMICOPS_PERSONAL/data/goals/*.md
$ACADEMICOPS_PERSONAL/data/context/*.md
$ACADEMICOPS_PERSONAL/data/sessions/*.json
$ACADEMICOPS_PERSONAL/data/views/current_view.json
```

**Priority guide**:
- P1: Today/tomorrow (action window closing, immediate blocker)
- P2: This week (important deadline, strategic value, prep needed)
- P3: Within 2 weeks (longer timeline, lower urgency)

## Session Logging (Automatic)

**Background**: Every session is automatically logged to daily JSON files to create a detailed history of work done. This helps track progress, maintain context across sessions, and associate work with tasks.

**Two-phase logging captures objectives and outcomes**:
1. **Planning phase** (PreToolUse hook on TodoWrite): Captures session objectives when you create todos
2. **Completion phase** (Stop hook): Captures what was actually accomplished

This dual approach focuses on high-level context (what we planned vs what we did) rather than low-level tracing (git handles that).

**How it works**:
1. When TodoWrite is called, a PreToolUse hook logs the session objectives automatically
2. When the session ends, a Stop hook analyzes the transcript (tools used, files modified, etc.)
3. Concise summaries are saved to `$ACADEMICOPS_PERSONAL/data/sessions/YYYY-MM-DD.json`
4. Entries can be associated with task IDs for progress tracking
5. Task files are updated with progress notes when applicable
6. File locking prevents race conditions when multiple sessions end simultaneously

**Session log structure**:
```json
{
  "session_id": "unique-session-id",
  "timestamp": "2025-10-24T12:34:56Z",
  "summary": "Extended session; used Read, Edit, Bash; modified 3 file(s)",
  "finished": false,
  "next_step": null,
  "task_id": null,
  "tools_used": ["Read", "Edit", "Bash"],
  "files_modified": ["/path/to/file1.py", "/path/to/file2.md"],
  "commands_run": ["git status", "pytest tests/"]
}
```

**Manual session logging** (optional):
```bash
# Log a session with custom summary
uv run python .claude/skills/task-management/scripts/session_log.py \
  --session-id "session-123" \
  --transcript "/path/to/transcript.jsonl" \
  --summary "Implemented session logging feature" \
  --finished \
  --next-step "Test the hook and commit changes" \
  --task-id "20251024-hostname-abc123" \
  --progress-note "Completed session logging implementation"
```

**Usage**:
- Automatic: Runs silently on every session stop
- No user interaction needed
- Logs stored in `$ACADEMICOPS_PERSONAL/data/sessions/` organized by date
- Review logs to see what was accomplished in previous sessions
- Associate sessions with tasks to track progress

**Integration with tasks**:
When a `task_id` is provided, the session log entry includes:
- Progress note added to task's `progress` array
- Task's `modified` timestamp updated
- Session ID linked for traceability
