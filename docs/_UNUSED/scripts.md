# Bot Scripts Documentation

This document provides details on the scripts available in `.academicOps/scripts/`.

## Email Interaction

**IMPORTANT**: Email interaction is handled via the `omcp` MCP server, NOT via scripts. See [OMCP-EMAIL](OMCP-EMAIL.md) for complete documentation.

Use MCP tools like `mcp__omcp__messages_search`, `mcp__omcp__messages_get`, etc. The old PowerShell scripts (`outlook-*.ps1`) are deprecated.

## `task_add.py`

**Purpose:** Creates a new task.

**Usage:**

```bash
uv run python .academicOps/scripts/task_add.py --title "Task Title" [--priority PRIORITY] [--project PROJECT_SLUG]
```

**Arguments:**

- `--title`: (string, required) The title of the task.
- `--priority`: (integer) The priority of the task.
- `--project`: (string) The slug of the project to associate the task with.

**Operational Notes:**

- Safe for parallel execution.

## `task_process.py`

**Purpose:** Processes tasks, primarily for email-related actions and archiving.

**Usage:**

```bash
uv run python .academicOps/scripts/task_process.py modify <task_id> [--archive] [--priority N] [--due YYYY-MM-DD]
```

**Arguments:**

- `<task_id>`: (string, required) The ID of the task to process (filename without .json extension).
- `--archive`: Archives the task by moving it to `data/tasks/archived/` and marking it with `archived_at` timestamp.
- `--priority N`: Updates the task priority.
- `--due YYYY-MM-DD`: Updates the task due date.

**Operational Notes:**

- Safe for parallel execution.
- Can handle both local tasks and email-based tasks.
- Archival is the standard completion method - there are only two states: active (inbox/queue) or archived.

## `task_index.py`

**Purpose:** Generates a compact, LLM-friendly index of all active tasks for background context.

**Usage:**

```bash
uv run python .academicOps/scripts/task_index.py [--format=text|json]
```

**Arguments:**

- `--format=text|json`: (optional) Output format. Defaults to `text`.

**Output:**

- **Text format**: Compact one-line-per-task format with priority, ID, due date, and title
- **JSON format**: Array of minimal task objects with id, priority, title, project, and due fields

**Operational Notes:**

- Safe for parallel execution.
- Designed for inclusion in strategist agent context without overwhelming token budgets.
- Sorted by priority (ascending), then due date (ascending).
- Use this for accomplishment matching and task awareness in background context.
