# Bot Scripts Documentation

This document provides details on the scripts available in `bot/scripts/`.

## Email Interaction

**IMPORTANT**: Email interaction is handled via the `omcp` MCP server, NOT via scripts. See [OMCP-EMAIL](OMCP-EMAIL.md) for complete documentation.

Use MCP tools like `mcp__omcp__messages_search`, `mcp__omcp__messages_get`, etc. The old PowerShell scripts (`outlook-*.ps1`) are deprecated.

## `task_add.py`

**Purpose:** Creates a new task.

**Usage:**
```bash
uv run python bot/scripts/task_add.py --title "Task Title" [--priority PRIORITY] [--project PROJECT_SLUG]
```

**Arguments:**
*   `--title`: (string, required) The title of the task.
*   `--priority`: (integer) The priority of the task.
*   `--project`: (string) The slug of the project to associate the task with.

**Operational Notes:**
*   Safe for parallel execution.

## `task_process.py`

**Purpose:** Processes tasks, primarily for email-related actions.

**Usage:**
```bash
uv run python bot/scripts/task_process.py modify <task_id> [--archive]
```

**Arguments:**
*   `<task_id>`: (string, required) The ID of the task to process.
*   `--archive`: Archives the task.

**Operational Notes:**
*   This script is primarily for email-related tasks. It can be used to archive local tasks, but it does not modify other task attributes.

## `task_complete.sh`

**Purpose:** Marks a task as complete and archives it.

**Usage:**
```bash
bot/scripts/task_complete.sh <task_filename>
```

**Arguments:**
*   `<task_filename>`: (string, required) The filename of the task to complete (e.g., `20250921-213541-nicwin-b2ca8699.json`).

**Operational Notes:**
*   **NOT parallel-safe.** This script performs a `git commit` and will fail if run concurrently.
*   This script will be updated to search for tasks in `inbox` and `queue` directories.
