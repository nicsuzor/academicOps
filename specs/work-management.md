---
title: Work Management Specification
status: active
created: 2026-01-12
updated: 2026-01-12
---

# Work Management Specification

This specification defines how the framework manages, tracks, and prioritizes work across multiple repositories and session boundaries.

## 1. Core Principles

1. **Task-First Execution**: Every non-trivial action must be associated with an active task.
2. **Hierarchical Decomposition**: Complex goals must be broken down into discrete, actionable steps.
3. **Graph-Aware Prioritization**: Work is prioritized based on dependency depth and blocking impact.
4. **Agent-Agnostic Context**: Task state must be stored in a portable, standard format (Markdown + YAML).

## 2. The Task Model

See `[[specs/tasks-v2]]` for the detailed task model.

### 2.1 Task Types

- **Goal**: Long-term objective (months).
- **Project**: Coherent body of work (weeks).
- **Epic**: Group of related tasks aimed at a milestone (days).
- **Task**: Discrete deliverable (hours).
- **Action**: Single work session (minutes).

### 2.2 Task Statuses

- **Inbox**: Captured but not yet triaged.
- **Active**: Ready to be worked on.
- **In Progress**: Currently being executed.
- **Blocked**: Waiting on a dependency.
- **Waiting**: Waiting on human decision or external input.
- **Review**: Work completed, awaiting verification.
- **Done**: Completed.
- **Cancelled**: Abandoned.

## 3. Assignment and Routing

Tasks are routed based on their `assignee` field:

| Role | Responsibility |
|---|---|
| `polecat` | Autonomous execution of mechanical tasks |
| `human` | Human tasks - requires judgment, external context |
| `null` | Unassigned (Inbox/Backlog) |

### 3.1 Routing Logic

1. **New Task capture** → `assignee: null` (captured in Inbox)
2. **Mechanical work** → `assignee: polecat`
3. **Human judgment required** → `assignee: human`

### 3.2 Example: Assigning to Human

```python
mcp__plugin_aops-core_task_manager__update_task(
    id="aops-12345",
    assignee="human"  # Human task
)
```

## 4. Query Patterns

Common patterns for finding and managing work:

### 4.1 Finding My Work (Human)

```python
mcp__plugin_aops-core_task_manager__list_tasks(project="aops", assignee="human")
```

### 4.2 Finding Ready Work (Agent)

```python
mcp__plugin_aops-core_task_manager__list_tasks(status="active", assignee="polecat")
```

## 5. Session Integration

Work management is integrated into the session lifecycle via hooks:

1. **SessionStart**: Injects active tasks and ready queue into initial context.
2. **UserPromptSubmit**: Correlates prompt with active task or identifies new task needs.
3. **AfterAgent**: Ensures accomplishments are logged against the active task.
4. **Stop**: Verifies task status transitions before closing session.
