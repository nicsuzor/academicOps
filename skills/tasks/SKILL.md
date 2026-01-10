---
name: tasks
category: instruction
description: Manage task lifecycle using scripts and MCP tools. Create, view, archive, and update properly formatted task files with structured metadata.
allowed-tools: Read,Grep,Glob,Edit,Write,Bash
version: 2.1.0
permalink: skills-tasks
---

# Task Management Skill

Responsible for [[data/tasks/tasks|tasks]]

## Authoritative Domain Knowledge

**Data Format**: Markdown (properly formatted) with YAML frontmatter
**Storage Location**: `data/tasks/*.md` in each repository
**Required Fields**: title, created, priority (0-3)
**Optional Fields**: due, project, classification
**Write Access**: Scripts (task_add.py, task_view.py, task_archive.py) OR memory server via remember skill - agents must not write task files directly via Edit/Write tools
**Scripts Location**: skills/tasks/scripts/
**Cross-Repo**: Each repository has independent data/tasks/ directory

Manage task lifecycle using scripts in this skill's `scripts/` directory or Tasks MCP server. Never write task files directly - always use the appropriate backend.

## Script Locations

Task scripts are located at `$AOPS/skills/tasks/scripts/`:

- `task_view.py` - View tasks
- `task_add.py` - Create tasks
- `task_update.py` - Update existing tasks
- `task_archive.py` - Archive/unarchive tasks

**IMPORTANT**: Always run scripts using `uv run` from the `$AOPS` directory:

```bash
cd $AOPS && uv run python skills/tasks/scripts/task_view.py
```

This ensures Python can find dependencies (yaml, etc.) from the project's virtual environment.

## TodoWrite vs Persistent Tasks

- **TodoWrite**: For tracking approved work steps within a single session only
- **This skill (tasks)**: For work requiring persistence, approval, or rollback capability

Use TodoWrite when you have an approved plan and are executing steps. Use this skill when creating work items that need to survive across sessions or require user approval.

## When to Use

Use this skill for:

- Viewing tasks ("What's urgent?", "Show my tasks")
- Archiving completed tasks
- Creating new tasks
- **Email-to-task workflow** ("Check my email for tasks" - see workflows/)

## Available Scripts

### task_view.py - View Tasks

Display tasks with filtering and sorting. Shows filenames in output for easy reference when archiving.

```bash
# Standard invocation (from $AOPS directory)
cd $AOPS && uv run python skills/tasks/scripts/task_view.py

# With options
cd $AOPS && uv run python skills/tasks/scripts/task_view.py --sort=due --per-page=20 --compact

# For testing with custom data directory
cd $AOPS && uv run python skills/tasks/scripts/task_view.py --data-dir=/path/to/data
```

**Output**: Formatted task list from `data/tasks/inbox/` with filenames displayed for each task.

**Options**:

- `--sort=priority|date|due`: Sort order (default: priority)
- `--per-page=N`: Number of tasks per page (default: 10, or 20 in compact mode)
- `--compact`: One-line-per-task view for quick triage
- `--data-dir=PATH`: Custom data directory (for testing)

### task_archive.py - Archive Completed Tasks

Move completed tasks to archive. **Supports batch operations** - can archive multiple tasks in one command.

```bash
# Archive a single task
cd $AOPS && uv run python skills/tasks/scripts/task_archive.py "task-filename.md"

# Archive multiple tasks (batch operation)
cd $AOPS && uv run python skills/tasks/scripts/task_archive.py "task1.md" "task2.md" "task3.md"

# Unarchive a task
cd $AOPS && uv run python skills/tasks/scripts/task_archive.py "task-filename.md" --unarchive

# For testing with custom data directory
cd $AOPS && uv run python skills/tasks/scripts/task_archive.py "task1.md" --data-dir=/path/to/data
```

**Parameters**:

- `filenames`: One or more task filenames (with or without .md extension)
- `--unarchive`: Move task(s) back to inbox
- `--data-dir=PATH`: Custom data directory (for testing)

**Output**: Reports success/failure for each task, with summary if multiple tasks processed.

### task_add.py - Create New Tasks

Create new task in inbox with properly formatted markdown.

```bash
# Basic task (filename uses sanitized title as slug)
cd $AOPS && uv run python skills/tasks/scripts/task_add.py \
  --title "Task title" \
  --priority 1 \
  --body "Task description with context"

# With explicit slug for custom filename
cd $AOPS && uv run python skills/tasks/scripts/task_add.py \
  --title "Complete important deliverable" \
  --slug "important-deliverable" \
  --priority 0 \
  --project "project-slug" \
  --classification "Action" \
  --due "2025-11-20T17:00:00Z" \
  --tags "urgent,important" \
  --body "Detailed context about the task"

# For testing with custom data directory
cd $AOPS && uv run python skills/tasks/scripts/task_add.py \
  --title "Test task" \
  --data-dir=/path/to/data
```

**Parameters**:

- `--title`: Task title (required)
- `--slug`: Custom slug for filename (default: sanitized title)
- `--priority`: 0-3 or P0-P3 (P0=urgent, P3=low)
- `--project`: Project slug for categorization
- `--classification`: Task type (Action, Review, Research, etc.)
- `--due`: Deadline in ISO8601 format
- `--tags`: Comma-separated tags
- `--body`: Task description/context (or use `--body-from-file`)
- `--data-dir`: Custom data directory (for testing)

**Output**: Creates task file in `data/tasks/inbox/` with properly formatted markdown

### task_item_add.py - Add Checklist Items

Add Obsidian Tasks-compatible checklist items to existing tasks. Creates a `## Checklist` section if needed. **Supports batch input** - can add multiple items in one call.

```bash
# Add single item
cd $AOPS && uv run python skills/tasks/scripts/task_item_add.py "task-filename.md" --item "Review draft"

# Add multiple items (batch - preferred for efficiency)
cd $AOPS && uv run python skills/tasks/scripts/task_item_add.py "task.md" \
  --item "First item" --item "Second item" --item "Third item"

# Add item with due date
cd $AOPS && uv run python skills/tasks/scripts/task_item_add.py "20251215-abc123" --item "Send email" --due 2025-01-15

# Add high-priority item
cd $AOPS && uv run python skills/tasks/scripts/task_item_add.py "#3" --item "Follow up" --priority high

# Mark item as already done
cd $AOPS && uv run python skills/tasks/scripts/task_item_add.py "task.md" --item "Completed step" --done
```

**Parameters**:

- `task_id`: Task identifier (filename, task ID, or #index from current view)
- `--item`: Item description (required, can specify multiple times for batch add)
- `--due`: Due date in YYYY-MM-DD format
- `--priority`: Priority level (high, medium, low)
- `--done`: Mark item as already completed
- `--data-dir`: Custom data directory (for testing)

**Output**: Appends checklist item to task's `## Checklist` section

### task_update.py - Update Existing Tasks

Modify fields on existing tasks (priority, title, project, tags, etc.).

```bash
# Update priority
cd $AOPS && uv run python skills/tasks/scripts/task_update.py "task-filename.md" --priority 0

# Update multiple fields
cd $AOPS && uv run python skills/tasks/scripts/task_update.py "task.md" --priority P1 --project "new-project"

# Manage tags
cd $AOPS && uv run python skills/tasks/scripts/task_update.py "task.md" --add-tags "urgent,review" --remove-tags "low-priority"
```

**Parameters**:

- `filename`: Task filename (required, first positional argument)
- `--priority`: New priority (0-3 or P0-P3)
- `--title`: New title
- `--project`: New project slug
- `--classification`: New classification
- `--due`: New deadline (ISO8601 format)
- `--status`: New status
- `--add-tags`: Comma-separated tags to add
- `--remove-tags`: Comma-separated tags to remove
- `--data-dir`: Custom data directory (for testing)

**Output**: Confirmation of modified fields

## Priority Levels

- **P0/0**: Urgent (today/tomorrow) - action window closing NOW
- **P1/1**: High (this week) - deadline within 7 days
- **P2/2**: Medium (within 2 weeks)
- **P3/3**: Low (longer timeline)

## Checklist Items (Dataview Format)

Tasks can contain checklists for tracking sub-actions. We use [Dataview inline fields](https://publish.obsidian.md/tasks/Reference/Task+Formats/About+Task+Formats) for Obsidian compatibility.

### Checklist Syntax

```markdown
## Checklist

- [ ] Uncompleted item
- [x] Completed item [completion:: 2025-01-10]
- [ ] Item with due date [due:: 2025-01-15]
- [ ] High priority item [priority:: high]
- [ ] Full example [priority:: medium] [due:: 2025-01-20]
- [/] In progress item
- [-] Cancelled item
```

### Dataview Fields

| Field      | Format                      | Example                     |
| ---------- | --------------------------- | --------------------------- |
| Due date   | `[due:: YYYY-MM-DD]`        | `[due:: 2025-01-15]`        |
| Completion | `[completion:: YYYY-MM-DD]` | `[completion:: 2025-01-10]` |
| Priority   | `[priority:: VALUE]`        | `[priority:: high]`         |

### When to Use Checklists

Use checklist items (not separate tasks) when:

- Sub-actions belong to a single deliverable
- Items share context/deadline with parent task
- Tracking granular progress on a larger task

Create separate tasks when:

- Items have independent deadlines
- Different projects or contexts
- Need separate priority/categorization

### Checklist Item Descriptions

**Items must be self-explanatory.** A reader should understand what needs to be done without clicking through to linked files.

❌ **Bad**: `P3: excalidraw` (what about it?)
✅ **Good**: `Write spec for excalidraw skill (diagram generation)`

Include: the action verb + the subject + brief context if not obvious from parent task.

## Task Workflow

**When user mentions completion**:

1. Archive task using filename from view output: `task_archive.py "filename.md"`
2. For multiple completions, use batch operation: `task_archive.py "task1.md" "task2.md" "task3.md"`
3. Verify task(s) moved to `data/tasks/archived/`

**When archiving a "Decision" task where user accepted work** (review invitation, collaboration request, etc.):

1. Archive the decision task
2. **Immediately create the follow-up action task** for the actual work (e.g., "Complete SNSF review" after accepting review invitation)
3. Do NOT ask if user wants the follow-up task - accepting work implies needing to do the work

**When user asks "what's urgent?"**:

1. Run: `task_view.py` to see inbox
2. Present output directly to user (includes filenames for easy reference)

## Before Creating Tasks

**MANDATORY**: Always check for existing related tasks before creating new ones.

```bash
# Search for existing tasks by keyword
grep -li "keyword" $ACA_DATA/tasks/inbox/*.md

# Or use task_view and grep
cd $AOPS && uv run python skills/tasks/scripts/task_view.py --compact | grep -i "keyword"
```

If a related task exists:

- **Use task_update.py** to modify priority, add context, or update fields
- **Do NOT create a duplicate** - this wastes user time on triage

This prevents the documented failure pattern where agents create duplicate tasks for the same work item.

## Critical Rules

**NEVER**:

- Write task markdown files directly
- Move files manually - use scripts
- Skip using scripts "because it's faster"
- Create a new task without first checking for existing related tasks

**ALWAYS**:

- Use scripts for ALL task operations
- Run from `$AOPS` directory: `cd $AOPS && uv run python skills/tasks/scripts/...`
- Verify script execution succeeded
- Search existing tasks before creating new ones (grep for keywords in title)
- Use task_update.py to modify existing tasks instead of creating duplicates

## Workflows

Comprehensive workflows that integrate task management with other systems:

### Email → Task Capture Workflow

**Location**: `workflows/email-capture.md`

**When to invoke**: User says "check my email for tasks", "process emails", or similar.

**What it does**:

1. Fetches recent emails via Outlook MCP
2. Analyzes content for action items
3. Queries memory server for context-aware categorization
4. Creates tasks automatically with proper project/priority/tags
5. Links tasks to source emails

**Backend**: Uses task_add.py script (or Tasks MCP when available)

**Key features**:

- Context-aware categorization using memory server
- Confidence scoring (high/medium/low)
- Priority inference from email signals
- Duplicate detection
- Email metadata linking

See `workflows/email-capture.md` for complete documentation.

## Task Backends

### Scripts Backend (Current Default)

Scripts in `~/.claude/skills/tasks/scripts/` provide CLI interface:

- **Availability**: Always (no dependencies)
- **Format**: properly formatted markdown
- **Use**: Development, testing, fallback

### MCP Backend (Optional)

Tasks MCP server provides tool interface:

- **Availability**: When `.mcp.json` configured and server running
- **Format**: Same properly formatted markdown
- **Use**: Production workflows, agent integration

**Backend selection**: Workflows check MCP availability and fall back to scripts automatically.

## Integration with Other Skills

This skill focuses on task _lifecycle_ (view, archive, create). Other skills handle:

- **Email workflow**: Email → Task extraction ([[workflows/email-capture.md]])
- **Session mining**: Extracting tasks from conversations (future)
- **Knowledge persistence**: Maintaining format and links (via [[remember]] skill)
