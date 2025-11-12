# Task Management MCP Server

FastMCP server providing task management tools for Claude Code and other MCP clients.

## Overview

This server exposes task management operations (view, archive, unarchive, create) via the Model Context Protocol (MCP). It provides a structured, type-safe interface to the task markdown files in `data/tasks/`.

**Status**: Production-ready **Version**: 1.0.0

## Features

- **View tasks** with filtering, sorting, and pagination
- **Archive/unarchive** tasks with batch support
- **Create tasks** with full metadata validation
- **Type-safe** using Pydantic models
- **Fail-fast** validation following AXIOMS.md principles
- **Structured logging** for monitoring and debugging

## Installation

### Prerequisites

- Python 3.11+
- `pydantic` and `pyyaml` packages

### Setup

1. Install dependencies:
   ```bash
   pip install --user pydantic pyyaml
   ```

2. Server is already configured in `.mcp.json`:
   ```json
   {
     "tasks": {
       "type": "stdio",
       "command": "python3",
       "args": ["bots/skills/tasks/server.py"],
       "env": {
         "ACA": "/home/nic/src/writing"
       }
     }
   }
   ```

3. Verify server starts:
   ```bash
   python3 bots/skills/tasks/server.py
   ```

## Task Identification

Tasks can be identified in multiple ways for maximum convenience:

### Index-based (zero friction)

After running `view_tasks`, refer to tasks by their displayed index:

```python
view_tasks()  # Shows tasks 1, 2, 3...
archive_tasks(identifiers=["3"])  # Archive task #3
```

**Benefits:**

- **Zero friction** - Natural "view then act" workflow
- **ADHD-friendly** - No need to remember/copy filenames
- **Intuitive** - Matches how you think about lists

**Requirements:**

- Must run `view_tasks` first to generate index mapping
- Indices valid until next `view_tasks` call
- Works for archive operations only (not unarchive)

### Filename-based (stable)

Use the task's filename or task ID for cross-session references:

```python
# Task ID (generated on creation)
archive_tasks(identifiers=["20251110-abc12345"])

# Full filename
archive_tasks(identifiers=["20251110-abc12345.md"])
```

**Benefits:**

- **Stable** - Never changes, works across sessions
- **Scriptable** - Reliable for automation
- **Explicit** - No ambiguity

### Mixed identifiers

Combine multiple formats in one operation:

```python
archive_tasks(identifiers=["1", "#3", "20251110-abc123", "task.md"])
```

## Available Tools

### `view_tasks`

View tasks with filtering, sorting, and pagination.

**Parameters:**

- `page` (int, default=1): Page number (1-indexed)
- `per_page` (int, default=10): Tasks per page (1-100)
- `sort` (str, default="priority"): Sort order - "priority", "date", or "due"
- `compact` (bool, default=false): Compact one-line format vs full details
- `priority_filter` (list[int], optional): Filter by priority levels (0-3)
- `project_filter` (str, optional): Filter by project slug
- `status_filter` (str, optional): Filter by status

**Returns:**

```json
{
  "success": true,
  "total_tasks": 15,
  "page": 1,
  "per_page": 10,
  "tasks": [
    {
      "title": "Task title",
      "priority": 1,
      "due": "2025-11-15T12:00:00Z",
      "status": "inbox",
      "filename": "20251110-abc123.md",
      ...
    }
  ],
  "message": "Showing 1-10 of 15 tasks"
}
```

**Example:**

```python
# View first 10 high-priority tasks
view_tasks(priority_filter=[1, 2], per_page=10)

# View tasks due soon
view_tasks(sort="due", per_page=20)

# View compact list of all tasks
view_tasks(compact=true, per_page=100)
```

### `archive_tasks`

Archive one or more tasks by moving them to archived folder.

**Parameters:**

- `identifiers` (list[str]): Task identifiers in any supported format:
  - **Index** (requires view_tasks first): `"3"`, `"#5"`
  - **Task ID** (with or without .md): `"20251110-abc123"`, `"20251110-abc123.md"`
  - **Filename**: `"20251110-abc123.md"`

**Returns:**

```json
{
  "success": true,
  "results": [
    {
      "success": true,
      "message": "Archived: task.md",
      "from": "tasks/inbox/task.md",
      "to": "tasks/archived/task.md",
      "resolved_from": "3"
    }
  ],
  "success_count": 1,
  "failure_count": 0
}
```

**Example:**

```python
# Zero-friction workflow: view then archive by index
view_tasks(priority_filter=[1, 2])
# See task #3 is done
archive_tasks(identifiers=["3"])

# Archive by task ID
archive_tasks(identifiers=["20251110-abc123"])

# Archive multiple tasks (mixed identifiers)
archive_tasks(identifiers=["1", "task2.md", "20251110-abc123"])
```

### `unarchive_tasks`

Unarchive one or more tasks by moving them back to inbox.

**Parameters:**

- `identifiers` (list[str]): Task identifiers:
  - **Task ID** (with or without .md): `"20251110-abc123"`, `"20251110-abc123.md"`
  - **Filename**: `"20251110-abc123.md"`

  Note: Index-based resolution not supported for archived tasks (not in current view).

**Returns:**

```json
{
  "success": true,
  "results": [
    {
      "success": true,
      "message": "Unarchived: task.md",
      "from": "tasks/archived/task.md",
      "to": "tasks/inbox/task.md",
      "resolved_from": "20251110-abc123"
    }
  ],
  "success_count": 1,
  "failure_count": 0
}
```

### `modify_task`

Modify an existing task without needing to archive and recreate.

**Parameters:**

- `identifier` (str): Task identifier (index, task ID, or filename)
- `title` (str, optional): New task title
- `priority` (int, optional): New priority 0-3
- `project` (str, optional): New project slug
- `classification` (str, optional): New classification
- `due` (str, optional): New due date in ISO format
- `status` (str, optional): New status
- `body` (str, optional): New body content
- `add_tags` (list[str], optional): Tags to add
- `remove_tags` (list[str], optional): Tags to remove

**Returns:**

```json
{
  "success": true,
  "message": "Modified task: 20251110-abc123.md",
  "modified_fields": ["priority", "tags (added)"],
  "task_id": "20251110-abc123"
}
```

**Example:**

```python
# Change priority of task #3
modify_task(identifier="3", priority=1)

# Update multiple fields
modify_task(
    identifier="20251110-abc123",
    title="Updated title",
    project="new-project",
    add_tags=["urgent"],
    remove_tags=["old-tag"]
)

# Just add a tag
modify_task(identifier="#5", add_tags=["in-progress"])
```

### `create_task`

Create a new task with generated ID and filename.

**Parameters:**

- `title` (str, required): Task title (non-empty)
- `priority` (int, optional): Priority level 0-3 (0=urgent, 3=low)
- `task_type` (str, default="todo"): Task type
- `project` (str, optional): Project slug for categorization
- `due` (str, optional): Due date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
- `body` (str, default=""): Task body content/description
- `tags` (list[str], optional): List of tags

**Returns:**

```json
{
  "success": true,
  "task_id": "20251110-abc12345",
  "filename": "20251110-abc12345.md",
  "path": "tasks/inbox/20251110-abc12345.md",
  "message": "Created task: 20251110-abc12345.md"
}
```

**Example:**

```python
# Create simple task
create_task(title="Review paper draft")

# Create task with full metadata
create_task(
    title="Submit grant application",
    priority=1,
    due="2025-11-20T17:00:00Z",
    project="grants",
    body="NSF grant deadline approaching",
    tags=["deadline", "high-stakes"]
)
```

## Architecture

```
┌─────────────────┐
│  Claude Code    │
│  (MCP Client)   │
└────────┬────────┘
         │ MCP Protocol (stdio)
         │
┌────────▼────────┐
│  FastMCP Server │
│  (server.py)    │
├─────────────────┤
│  Tools:         │
│  - view_tasks   │
│  - archive_tasks│
│  - unarchive_tasks│
│  - create_task  │
└────────┬────────┘
         │
┌────────▼────────┐
│  Task Library   │
│  (task_ops.py)  │
├─────────────────┤
│  - load_tasks() │
│  - save_task()  │
│  - archive()    │
└────────┬────────┘
         │
┌────────▼────────┐
│  File System    │
│  data/tasks/    │
└─────────────────┘
```

## Task File Format

Tasks are stored in **bmem-compliant** markdown format with structured YAML frontmatter and body sections.

### Bmem Format Structure

```markdown
---
title: "Task title"
permalink: 20251110-abc123-1
type: task
tags: [action, priority]
created: "2025-11-10T12:00:00Z"
modified: "2025-11-10T13:00:00Z"
task_id: 20251110-abc123
priority: 1
status: inbox
classification: Action
project: "project-slug"
due: "2025-11-15T12:00:00Z"
aliases: [20251110-abc123]
---

# Task title

## Context

Task description and context goes here. Can include multiple paragraphs and markdown formatting.

## Observations

- [task] Task title #status-inbox #priority-p1
- [project] Project: project-slug #project-project-slug

## Relations
```

### Field Descriptions

**Required frontmatter:**

- `title`: Task title
- `permalink`: Unique bmem permalink (taskid-1 format)
- `type`: Always "task" for bmem compliance
- `task_id`: Task identifier (YYYYMMDD-xxxxxxxx)
- `created`: ISO 8601 timestamp
- `modified`: ISO 8601 timestamp (auto-updated)
- `status`: Task status (inbox, queue, archived)
- `aliases`: List with task_id for linking

**Optional frontmatter:**

- `priority`: 0-3 (0=urgent, 1=high, 2=medium, 3=low)
- `classification`: Task classification (Action, Research, etc.)
- `project`: Project slug
- `due`: ISO 8601 timestamp
- `archived_at`: ISO 8601 timestamp (set automatically)
- `tags`: List of tags
- `metadata`: Dict for custom metadata

**Body structure:**

- `# Title`: H1 heading with task title
- `## Context`: Task description and details
- `## Observations`: Categorized facts with #tags (auto-generated, don't duplicate metadata)
- `## Relations`: Links to related entities (optional)

### Bmem Compliance

This format ensures compatibility with:

- **Obsidian**: Full vault integration and linking
- **bmem tools**: Knowledge base management
- **Basic-memory MCP**: Memory persistence

Per CLAUDE.md: "All markdown in data/ must use bmem format"

## Error Handling

The server follows fail-fast principles:

**Fail-fast errors** (halt immediately):

- Data directory not found
- Invalid task file format
- Missing required fields
- Invalid input parameters

**Graceful handling**:

- Task not found returns success=false with message
- Batch operations report per-file results
- Optional fields default to None/empty

**Error response format:**

```json
{
  "success": false,
  "error_type": "TaskNotFoundError",
  "message": "Task file not found: task.md",
  "context": {
    "searched_paths": "data/tasks/inbox, data/tasks/queue"
  }
}
```

## Logging

Server logs to stdout in structured format:

```
2025-11-10T12:34:56 - task-manager - INFO - view_tasks: page=1, total=15
2025-11-10T12:35:01 - task-manager - INFO - archive_tasks: 2 succeeded, 0 failed
```

Log levels:

- **INFO**: Normal operations
- **ERROR**: Failures and exceptions
- **DEBUG**: Detailed debugging (not enabled by default)

## Development

### Running Tests

Tests are located in `tests/test_task_ops.py`:

```bash
# Run all tests
pytest tests/test_task_ops.py -v

# Run specific test
pytest tests/test_task_ops.py::test_archive_task -v
```

### Code Quality

```bash
# Type checking
mypy bots/skills/tasks/

# Linting
ruff check bots/skills/tasks/

# Format checking
ruff format --check bots/skills/tasks/
```

### Development Server

Run server directly for testing:

```bash
# Set data directory
export ACA=/home/nic/src/writing

# Run server
python3 bots/skills/tasks/server.py
```

## Troubleshooting

### Server won't start

**Error: "No module named 'pydantic'"**

Solution:

```bash
pip install --user pydantic pyyaml
```

**Error: "Data directory not found"**

Solution: Set `ACA` environment variable or create `./data` directory

```bash
export ACA=/home/nic/src/writing
```

### Tasks not appearing in view_tasks

**Check:**

1. Tasks are in `data/tasks/inbox/` or `data/tasks/queue/`
2. Files have `.md` extension
3. Files have valid YAML frontmatter
4. Tasks don't have `archived_at` field set

**Debug:**

```bash
# Check file format
head -20 data/tasks/inbox/task.md

# Verify frontmatter is valid YAML
grep -A 20 "^---" data/tasks/inbox/task.md | head -20
```

### Index resolution fails

**Error: "Cannot resolve index #3: no current view"**

Solution: Run `view_tasks` first to generate the index mapping

```python
# Correct order
view_tasks()  # Generate index mapping
archive_tasks(identifiers=["3"])  # Now index resolves

# Won't work - no view yet
archive_tasks(identifiers=["3"])  # Error: no current view
```

**Error: "Index #5 not found in current view"**

Solution: The index is outside the current view range. Either:

- Use a different page: `view_tasks(page=2)`
- Use more results per page: `view_tasks(per_page=20)`
- Use the stable filename instead: `archive_tasks(identifiers=["20251110-abc123"])`

### Archive operation fails

**Error: "Task not found"**

Solution: Check identifier format

```python
# Correct - use index, task ID, or filename
archive_tasks(identifiers=["3"])
archive_tasks(identifiers=["20251110-abc123"])
archive_tasks(identifiers=["20251110-abc123.md"])

# Incorrect - don't use full path
archive_tasks(identifiers=["data/tasks/inbox/20251110-abc123.md"])
```

## CLI Scripts (Alternative Interface)

The original CLI scripts are still available for direct command-line use:

```bash
# View tasks
uv run python bots/skills/tasks/scripts/task_view.py

# Archive task
uv run python bots/skills/tasks/scripts/task_archive.py task.md

# Add task
uv run python bots/skills/tasks/scripts/task_add.py --title "Task title" --priority 1
```

**Note**: MCP tools are now the recommended interface for agent interactions.

## Related Documentation

- **Specification**: `data/tasks/inbox/fastmcp-task-server-spec.md`
- **Task skill**: `bots/skills/tasks/SKILL.md`
- **Framework**: `bots/skills/framework/SKILL.md`
- **MCP config**: `.mcp.json`

## Version History

**1.2.0** (2025-11-10)

- **Bmem-compliant task format** - All tasks now use proper bmem structure
- **modify_task tool** - Sophisticated editing without archive/recreate
- Proper frontmatter (permalink, task_id, aliases, modified timestamp)
- Structured body (# Title, ## Context, ## Observations, ## Relations)
- Context section extraction for body content
- No duplication of metadata in Observations
- Partial updates (only change specified fields)
- Tag add/remove operations
- Obsidian and bmem tools compatibility

**1.1.0** (2025-11-10)

- **Index-based task resolution** - Archive tasks by index from current view
- Zero-friction "view then act" workflow
- Mixed identifier support (index + filename in same call)
- Enhanced error messages for identifier resolution
- Updated documentation with identification strategies

**1.0.0** (2025-11-10)

- Initial release
- Tools: view_tasks, archive_tasks, unarchive_tasks, create_task
- Pydantic validation
- Fail-fast error handling
- Structured logging
