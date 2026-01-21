---
title: Framework Paths and Configuration
type: instruction
description: Session-resolved paths and environment configuration. Injected at session start.
---

## Python Tooling

**Always use `uv run`** for Python commands in this framework:
- `uv run python script.py` (not `python script.py`)
- `uv run pytest tests/` (not `pytest tests/`)
- `uv run ruff check .` (not `ruff check .`)

This ensures the correct virtual environment and dependencies are used without manual activation.

## Memory System

User memories are strictly organised with a clear distinction between:

- **Episodic Memory** (Observations): Time-stamped events, what happened when. "I tried X and it failed." "Meeting decided Y."
- **Semantic Memory** (Current State): Timeless truths, always up-to-date. "X doesn't work because Y." "Our approach is Z."

### Three Storage Systems

| System | Purpose | When to Use |
|--------|---------|-------------|
| **Tasks MCP** | Operational tracking | Tasks, bugs, observations, experiments, decisions-in-progress |
| **$ACA_DATA markdown** | Knowledge SSoT | Synthesized truths, project context, goals, general knowledge |
| **Memory server** | Semantic search index | Markdown + completed tasks with learnings - enables `mcp__memory__retrieve_memory` |

### Automatic Sync: Completed Tasks → Memory

When a task is completed with documented learning, it's searchable alongside synthesized knowledge.

- **Tagged**: `task`, `completed`, `type:<task_type>`, `priority:P<n>`
- **Content**: Title, body, completion context
- **Search**: `mcp__memory__retrieve_memory(query="...")` finds both markdown AND task learnings

### Decision Tree

```
Is this a task or observation? (time-stamped, "agent did X")
  → YES: mcp__plugin_aops-core_tasks__create_task() or update_task() (NOT remember skill)

Is this synthesized knowledge? (timeless truth, "X is Y")
  → YES: Skill(skill="remember") → writes markdown + memory server

Need to search existing knowledge?
  → USE: mcp__memory__retrieve_memory(query="...")
```

### Key Rules

1. **Memory is the knowledge source** - Agents MUST check `mcp__memory__retrieve_memory` when starting tasks or needing context. This is how you access user knowledge, project history, and learned patterns. Don't guess - search memory first.
2. **Markdown is SSoT** - Memory server is derived, not authoritative
3. **Remember skill dual-writes** - Always use it for new knowledge (ensures sync)
4. **Tasks for observations** - Don't create markdown files for time-stamped events
5. **Synthesis flow**: task observations → patterns emerge → remember skill → semantic docs → complete task

### Graph Connectivity

Tasks must use `[[wikilinks]]` in the body for entities that should be connected in the knowledge graph. Tags alone are insufficient for graph connectivity.

**Example**: "Recovered database for [[Client Name]]" - not just tagging with "Client Name".

### Blocking Relationships

When work X blocks work Y:
1. Create task for Y (the blocked work) if it doesn't exist
2. Set Y's `depends_on=["<X-task-id>"]`
3. Optionally note context in Y's body about why it's blocked

**Don't**: Add "BLOCKING: Y" notes to X's body - that's prose, not structure.
**Do**: Create Y with `depends_on=[X]` - that's queryable via `get_blocked_tasks()`.

### Insight Capture

When you discover something worth preserving:
- **Operational insight** (bug found, approach tried): `mcp__plugin_aops-core_tasks__create_task()` or update existing task
- **Knowledge insight** (pattern, principle, fact): `Skill(skill="remember")`
- **Both**: Create task for tracking, use remember skill for the knowledge

**To persist knowledge**: Use `Skill(skill="remember")` (blocking) or spawn background Task with `run_in_background=true` (seamless).

**To search**: Use `mcp__memory__retrieve_memory(query="...")`.

**To repair sync**: Run remember skill's sync workflow (reconciles markdown → memory server).

### Task Queries

When looking for tasks:

| Intent | Tool | Example |
|--------|------|---------|
| Find by keyword | `search_tasks(query="...")` | Find tasks mentioning "observability" |
| List all in project | `list_tasks(project="aops")` | See all tasks regardless of status |
| List ready to work on | `get_ready_tasks()` | Leaves with no blockers |
| List blocked | `get_blocked_tasks()` | Tasks waiting on dependencies |

**Caution**: `list_tasks(status="active")` returns ONLY tasks explicitly marked "active". Most tasks are "inbox" (default) or "done". Use `search_tasks` for keyword search or omit status filter to see all.

### Task Assignment

Use **tags** for task assignment:
- `tags: ["bot"]` - automated/agent work
- `tags: ["human"]` - manual/user work

Don't use the `context` field for assignment - it's for general task context notes.

## Submodule Handling

`$AOPS` (aops/) is a **git submodule**. When modifying files in aops/:
- Run git commands from within the submodule: `cd $AOPS && git status`
- Commit in the submodule first, then update the parent repo's submodule reference
- Parent repo's `git status` won't show aops changes (submodule is `ignore = all`)

## File Location Conventions

| Content Type | Location | Example |
|-------------|----------|---------|
| aops feature specs | `$AOPS/specs/` | `$AOPS/specs/task-graph-network-v1.0.md` |
| User knowledge/designs | `$ACA_DATA/designs/` | `$ACA_DATA/designs/my-project-design.md` |
| Generated outputs | `$ACA_DATA/outputs/` | `$ACA_DATA/outputs/task-viz.excalidraw` |

**Rule**: aops framework features follow the feature-development workflow and specs go in `$AOPS/specs/`. User project designs go in `$ACA_DATA/designs/`.
