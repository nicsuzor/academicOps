---
name: tasks
category: instruction
description: Manage hierarchical task lifecycle using the task CLI or MCP server. Supports graph-based decomposition and project-aware storage.
allowed-tools: Read,Grep,Glob,Edit,Write,Bash,Task
version: 3.0.0
permalink: skills-tasks
---

# Task Management Skill (v2)

Responsible for managing the hierarchical task system as defined in [[specs/tasks-v2|Tasks v2]].

## Design Philosophy

- **Markdown Source of Truth**: Every task is a `.md` file with YAML frontmatter.
- **Project-Based Storage**: Tasks are stored flat in `$ACA_DATA/<project>/tasks/`.
- **Graph-First**: Relationships (parent, depends_on) are explicit in metadata.
- **Hierarchical**: Tasks are semantic (Goal → Project → Task → Action).
- **Index-Accelerated**: Fast queries via a global `index.json`.

## Storage Locations

- **Projects**: `$ACA_DATA/<project>/tasks/*.md`
- **Inbox**: `$ACA_DATA/tasks/inbox/*.md`
- **Index**: `$ACA_DATA/tasks/index.json`

## Authoritative Tools

### 1. Task CLI (`aops-core/scripts/task.py`)

The primary CLI for manual management. Always run via `uv run python`.

```bash
# Add a goal
uv run python aops-core/scripts/task.py add "Finish Thesis" --type=goal --project=hdr

# Decompose into projects
uv run python aops-core/scripts/task.py decompose <goal-id> -t "Chapter 1" -t "Chapter 2" --sequential

# View ready tasks
uv run python aops-core/scripts/task.py ready

# Show task tree
uv run python aops-core/scripts/task.py tree <id>

# Rebuild index (if status looks stale)
uv run python aops-core/scripts/task.py index rebuild
```

### 2. MCP Server (`aops-core/skills/tasks/server.py`)

Provides tools for agents (Claude, Gemini) to manage tasks.

- `create_task`: Create a task with graph metadata.
- `decompose_task`: Split a task into ordered subtasks.
- `get_ready_tasks`: Fetch tasks with satisfied dependencies.
- `get_task_tree`: Fetch recursive hierarchy.
- `update_task`: Modify any field including graph links.

## Task States

- **inbox**: Captured but not committed.
- **active**: Workable (no blockers/children).
- **blocked**: Waiting on a dependency.
- **waiting**: Waiting on external input.
- **done**: Completed.
- **cancelled**: Abandoned.

## Rules for Agents

1. **NO WORKAROUNDS**: Never write task files directly via `write_file`. Always use the CLI or MCP tools.
2. **SEARCH FIRST**: Use `grep` or `list_tasks` to check for existing tasks before creating duplicates.
3. **RELATIONAL INTEGRITY**: When creating child tasks, the system automatically handles `leaf` status and `depth`.
4. **PROJECT NAMESPACES**: Assign tasks to projects whenever possible.
5. **SEQUENTIAL WORKFLOWS**: Use `--sequential` in `decompose` or `depends_on` in tools to create dependency chains.
