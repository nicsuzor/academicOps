---
name: tasks
description: Script-based task lifecycle operations. Handles creation, prioritization, progress tracking, completion, and strategic alignment using task scripts ONLY. Never writes files directly.
license: Apache 2.0
permalink: aops/skills/tasks/skill
---

# Task Management via Scripts

## Overview

Manages complete task lifecycle using Python scripts in `$AOPS/scripts/task_*.py`. Uses scripts for ALL operations - never writes task files directly.

**Core principle**: Tasks must link to goals. Scripts are the single interface to task data.

**Integration**: Invoked by scribe skill when session mining identifies tasks.

## When to Use This Skill

**Invoked for**:
- Creating tasks from extracted information
- Updating task priority, due dates, status
- Archiving completed tasks
- Viewing/displaying task lists
- Strategic alignment checks
- Duplicate prevention

**NOT invoked for**:
- Session mining (scribe does this)
- Extracting tasks from conversations (scribe does this)
- Writing non-task bmem files (scribe does this)

## Task Scripts Reference

All scripts located in `$AOPS/scripts/`. Use `uv run python <script>` to execute.

### task_add.py - Create New Tasks

**Purpose**: Create new task file in `data/tasks/inbox/`.

**Usage**:
```bash
uv run python $AOPS/scripts/task_add.py \
  --title "Prepare keynote slides" \
  --priority 2 \
  --project "academic-profile" \
  --due "2025-11-15" \
  --summary "Create slides for conference X. Focus on accountability frameworks."
```

**Parameters**:
- `--title` (required): Action-oriented task title (see guidelines below)
- `--priority`: Priority level
  - Accepts: 0-3 or P0-P3
  - P0/0 = Urgent (today/tomorrow)
  - P1/1 = High (this week)
  - P2/2 = Medium (within 2 weeks)
  - P3/3 = Low (longer timeline)
- `--type`: Task type (default: "todo")
  - Examples: todo, meeting, deadline, review, writing
- `--project`: Project slug (must match filename in data/projects/)
- `--due`: Due date in ISO8601 format (YYYY-MM-DD)
- `--summary` or `--details`: Detailed task context
- `--details-from-file`: Path to file containing summary
- `--preview`: Short preview text (optional)
- `--metadata`: JSON string for additional metadata (optional)

**Output**: Creates `data/tasks/inbox/[TASK_ID].md` with Basic Memory format.

**Task ID format**: `YYYYMMDD-HHMMSS-hostname-uuid`

### task_view.py - View Tasks

**Purpose**: Display tasks with pagination, sorting, and filtering.

**Usage**:
```bash
# Default: page 1, sort by priority, 10 per page
uv run python $AOPS/scripts/task_view.py

# Page 2, sort by due date, 20 per page
uv run python $AOPS/scripts/task_view.py 2 --sort=due --per-page=20

# Compact view (one line per task)
uv run python $AOPS/scripts/task_view.py --compact

# Sort by creation date
uv run python $AOPS/scripts/task_view.py --sort=date
```

**Parameters**:
- `[page]`: Page number (positional, default: 1)
- `--sort=priority|date|due`: Sort field
  - `priority`: By priority number (ascending: P0 first)
  - `date`: By creation date (descending: newest first)
  - `due`: By due date (ascending: soonest first, None last)
- `--per-page=N`: Results per page (default: 10, or 20 in compact mode)
- `--compact`: One-line-per-task view for quick triage

**Output**: Formatted task list with color coding. Creates `data/views/current_view.json`.

**CRITICAL for Display Mode**: When user asks to see tasks, present the ACTUAL OUTPUT directly. The script is designed for human readability - don't summarize or reformat.

### task_index.py - Compact Overview

**Purpose**: Generate compact task summary.

**Usage**:
```bash
uv run python $AOPS/scripts/task_index.py
```

**Parameters**: None

**Output**: High-level task count by priority and status. Fast overview for context loading.

### task_process.py - Modify Tasks

**Purpose**: Update existing tasks (priority, due date) or archive them.

**Usage**:
```bash
# Update priority
uv run python $AOPS/scripts/task_process.py modify <task_id> --priority 1

# Update due date
uv run python $AOPS/scripts/task_process.py modify <task_id> --due "2025-11-20"

# Archive completed task
uv run python $AOPS/scripts/task_process.py modify <task_id> --archive
```

**Parameters**:
- `modify`: Subcommand (required)
- `<task_id>`: Task ID to modify (required)
- `--priority`: New priority (0-3 or P0-P3)
- `--due`: New due date (YYYY-MM-DD)
- `--archive`: Archive the task (moves to data/tasks/archived/)

**Output**: Updates task file in place or moves to archived/ directory.

### Other Task Scripts

**task_search.py**: Search tasks by keyword (if implemented)
**task_create.py**: Alternative task creation interface (if different from task_add.py)
**task_modify.py**: Alternative modification interface (if different from task_process.py)
**task_archive.py**: Direct archiving (may be alias for task_process.py --archive)
**task_convert.py**: Convert task formats (legacy → current)

**Note**: Always check script exists before invoking. Use task_add.py, task_view.py, and task_process.py as primary interfaces.

## Prioritization Framework

### Priority Levels (P0-P3)

**P0 (Urgent - Today/Tomorrow)**:
- Action window closing NOW (not just deadline approaching)
- Meeting prep due within 24 hours
- Immediate blocker for others
- Time-sensitive response needed
- Someone waiting on you RIGHT NOW

**P1 (High - This Week)**:
- Deadline within 7 days
- Significant strategic value
- Preparation needed soon
- Collaborative work where others waiting
- Important but not urgent TODAY

**P2 (Medium - Within 2 Weeks)**:
- Deadline within 14 days
- Moderate strategic alignment
- Can wait a few days without impact
- Standard workflow items

**P3 (Low - Longer Timeline)**:
- Longer timeline (>2 weeks)
- Lower strategic alignment
- No immediate action window
- Nice-to-have items
- Future exploration

### Key Prioritization Factors

**In order of importance**:

1. **Temporal constraints**: Due date, action window, meeting dates
   - **Critical distinction**: Deadline vs action window
   - Task due Friday may need action TODAY if delay reduces effectiveness
   - Example: Conference talk due Friday → slides need review by Wednesday → start Monday (P0 on Monday)

2. **Strategic alignment**: Does it link to goals?
   - Check `data/goals/*.md` for linkage
   - P0/P1 tasks MUST link to goals
   - If no goal link → consider lowering priority or creating goal

3. **Dependencies & roles**: Who's waiting? What's your role?
   - Supervisor request → often P0 or P1
   - Student request → assess urgency + strategic value
   - Admin request → often P2 or P3 unless time-sensitive
   - Blocker for others → increase priority

## Task Title Guidelines

**Formula**: `[Action Verb] + [Specific Object] + [Optional Context]`

**DO**:
- Use action verbs: "Prepare", "Review", "Respond to", "Submit", "Confirm"
- Be specific and scannable
- Keep concise (1-8 words)
- Make it clear what action is needed

**DON'T**:
- Write "Email from X about Y" (not action-oriented)
- Include strategic analysis in title
- Be vague ("Handle things", "Follow up")
- Repeat context that belongs in summary

**Examples**:

✅ **GOOD**:
- "Confirm keynote for Platform Governance Conference"
- "Review student thesis Chapter 3 and schedule meeting"
- "Submit talk title for November conference"
- "Respond to conference invitation from Dr. Smith"

❌ **BAD**:
- "Email about conference" (what action?)
- "Student wants to meet" (what's needed?)
- "Handle administrative stuff" (too vague)
- "Important deadline approaching" (what is it?)

## Task Summary Writing

**Write for the USER, not for strategic analysis.**

### What to Include

- What needs to be done (briefly - title already covers this)
- Why it matters (1 sentence)
- When it's due or action window
- Where to find materials (direct links so user doesn't need to search emails)
- Any specific constraints or requirements

### What NOT to Include

- Strategic analysis of priority choices (internal use only)
- Explanations of relationships user already knows
- Role definitions or organizational hierarchy
- Lengthy dependency chains
- Duplicate information from frontmatter

### Good Examples

✅ "Review Joel's chapter draft on marginal value of films (https://sharepoint.com/...). Focus on storytelling and platform realities. Provide feedback before supervision meeting."

✅ "Prepare keynote slides for Nov 15 conference. Focus on accountability frameworks. Review with team by Nov 10."

✅ "Student requesting feedback on Chapter 3 draft. Schedule meeting this week."

### Bad Examples

❌ "As the invited keynote speaker for the conference on Nov 15, which aligns with your Academic Profile goal and was mentioned in your current priorities as a strategic initiative for increasing research visibility in the platform governance space, you need to prepare slides focusing on your recent work on accountability frameworks because this represents a key opportunity to advance Goal 2..."

❌ "Meeting request from PhD student (supervision context, Academic Profile goal) regarding Chapter 3 thesis feedback. This represents a P2 priority supervision task that requires review of draft materials and coordination of schedules to ensure timely progress on thesis milestones..."

**Detail level**: Write what the user needs to take action, nothing more. "Weekly standup level" for context.

## Strategic Alignment Enforcement

**CRITICAL**: P0 and P1 tasks MUST link to goals.

### Verification Workflow

When creating/prioritizing P0 or P1 tasks:

1. **Check project link**: Does `--project` parameter match a file in `data/projects/`?
2. **Verify project → goal linkage**: Read project file, check Relations section for goal link
3. **Validate goal exists**: Read `data/goals/[goal].md`
4. **Confirm bidirectional link**: Goal file should list project

### If Misaligned

**Create task anyway** (don't block user) but:
1. Add observation noting misalignment
2. Flag to user: "I notice this P1 task claims to support [Goal X], but it's not listed in that goal's file. Should we: a) Add it to the goal (confirm strategic importance) b) Lower priority (not strategically aligned)"

**Strategic context to check**:
- `data/goals/*.md` - Verify strategic goals
- `data/projects/*.md` - Find related projects
- `data/context/current-priorities.md` - Current focus

**Alignment validation is a CHECK, not a BLOCKER**.

## Duplicate Prevention

**ALWAYS check for duplicates BEFORE creating tasks.**

### Duplicate Check Workflow

1. **Run task_view.py** to see recent tasks:
   ```bash
   uv run python $AOPS/scripts/task_view.py --per-page=50
   ```

2. **Review output** for similar:
   - Task titles (semantic similarity, not just exact match)
   - Projects
   - Due dates
   - Summaries

3. **If similar task exists**:
   - **Update** existing task instead (change priority, due date)
   - **Don't create** duplicate

4. **If no duplicate**:
   - Proceed with task_add.py

**Semantic matching**: "Prepare keynote" and "Create conference slides" may be the same task - use judgment.

## Task Lifecycle Workflows

### Creating Task (Full Workflow)

```bash
# 1. Check for duplicates
uv run python $AOPS/scripts/task_view.py --per-page=50
# Review output, verify no duplicate

# 2. Create task
uv run python $AOPS/scripts/task_add.py \
  --title "Prepare keynote slides" \
  --priority 1 \
  --project "academic-profile" \
  --due "2025-11-15" \
  --summary "Create slides for Platform Governance Conference. Focus on accountability frameworks. Materials at https://email.link/..."

# 3. Verify strategic alignment
# Read data/projects/academic-profile.md
# Check Relations section for goal link
# If P0/P1 and no goal link → flag misalignment
```

### Updating Task

```bash
# 1. Find task ID from task_view.py output
uv run python $AOPS/scripts/task_view.py

# 2. Update priority
uv run python $AOPS/scripts/task_process.py modify 20251108-143022-hostname-abc123 --priority 0

# 3. Update due date
uv run python $AOPS/scripts/task_process.py modify 20251108-143022-hostname-abc123 --due "2025-11-10"
```

### Archiving Task (Completion)

```bash
# When user mentions completion:

# 1. Archive task
uv run python $AOPS/scripts/task_process.py modify <task_id> --archive

# 2. Invoke scribe skill to update accomplishments
# (scribe writes to data/context/accomplishments.md)
```

## Integration with Scribe Skill

### Division of Responsibilities

**Scribe skill**:
- Extracts task information from sessions
- Identifies when tasks are mentioned
- Invokes tasks skill with extracted information
- Updates accomplishments.md when tasks completed
- Updates non-task bmem files (projects, goals, context)

**Tasks skill (this)**:
- Runs task scripts
- Creates task files via task_add.py
- Updates tasks via task_process.py
- Archives tasks via task_process.py --archive
- Displays tasks via task_view.py
- Checks strategic alignment
- Prevents duplicates

### Invocation Pattern

When scribe extracts task information:

```
Scribe mines session → identifies task → invokes tasks skill
                                                ↓
Tasks skill → checks duplicates → runs task_add.py → validates alignment
```

When scribe detects completion:

```
Scribe detects "completed X" → invokes tasks skill to archive
                                       ↓
Tasks skill → runs task_process.py --archive
            ↓
Scribe → writes to accomplishments.md
```

## Critical Rules

**NEVER**:
- Write task files directly (always use scripts)
- Create tasks without checking duplicates first
- Skip strategic alignment checks for P0/P1 tasks
- Include strategic analysis in user-facing summaries
- Use context-search or bmem-ops (use scripts instead)
- Batch task operations (create/archive immediately)
- Mark tasks as P0/P1 without goal linkage (flag instead)

**ALWAYS**:
- Use scripts for ALL task operations
- Check duplicates before creating (task_view.py)
- Use action-oriented titles
- Link P0/P1 tasks to projects and goals
- Keep summaries brief and user-focused
- Archive completed tasks promptly (task_process.py)
- Verify scripts exist before invoking
- Present task_view.py output DIRECTLY to user (don't reformat)

## Quick Reference

**Most common operations**:

```bash
# Create task
uv run python $AOPS/scripts/task_add.py --title "..." --priority N --project "..." --due "YYYY-MM-DD" --summary "..."

# View tasks
uv run python $AOPS/scripts/task_view.py --per-page=20

# Compact overview
uv run python $AOPS/scripts/task_index.py

# Update priority
uv run python $AOPS/scripts/task_process.py modify <task_id> --priority N

# Archive task
uv run python $AOPS/scripts/task_process.py modify <task_id> --archive
```

**Priority decision tree**:

```
Q: Action window closing within 24 hours?
YES → P0

Q: Deadline within 7 days OR high strategic value?
YES → P1

Q: Deadline within 14 days OR moderate alignment?
YES → P2

Q: Longer timeline OR lower alignment?
YES → P3
```

**Data paths**:

```
$AO/data/tasks/inbox/      # New tasks
$AO/data/tasks/queue/      # Prioritized (if used)
$AO/data/tasks/archived/   # Completed
$AO/data/projects/*.md     # For task→project linkage
$AO/data/goals/*.md        # For project→goal linkage
$AO/data/views/current_view.json  # Generated by task_view.py
```

## Success Criteria

This skill succeeds when:
1. **Script-based operations** - All task operations use scripts, never direct file writes
2. **No duplicates** - Duplicate check happens before every create
3. **Strategic alignment** - P0/P1 tasks linked to goals, misalignments flagged
4. **Accurate priorities** - P0-P3 reflect true importance + urgency + alignment
5. **Quality titles/summaries** - Action-oriented, user-focused, scannable
6. **Immediate operations** - Tasks created/archived as soon as identified (no batching)
