---
title: Work Management: Tasks MCP
type: spec
status: active
tier: data
depends_on: []
tags: [spec, tasks, mcp, data]
---

# Work Management: Tasks MCP

## Giving Effect

- PKB MCP server (Rust, `nicsuzor/mem`) implementing task CRUD and graph operations
- [[mcp__pkb__create_task]] - Create task
- [[mcp__pkb__update_task]] - Update task fields (priority, tags, assignee, body)
- [[mcp__pkb__release_task]] - Release task to handoff status with required summary
- [[mcp__pkb__complete_task]] - Mark task done with completion evidence
- [[mcp__pkb__list_tasks]] - List tasks with filters
- [[commands/pull.md]] - `/pull` command for claiming and executing tasks
- [[commands/dump.md]] - `/dump` command for session handover

Tasks MCP is the primary work management system for multi-session tracking, dependencies, and strategic work.

```mermaid
flowchart LR
    subgraph CREATE["Create Work"]
        C1[create_task]
        C2[list_tasks]
    end

    subgraph CLAIM["Claim"]
        E1["update_task(status=in_progress)"]
    end

    subgraph EXECUTE["Execute"]
        E2[Work on task]
    end

    subgraph RELEASE["Release"]
        R1["release_task(merge_ready)"]
        R2["release_task(done)"]
        R3["release_task(blocked)"]
    end

    C1 --> C2 --> E1 --> E2
    E2 --> R1
    E2 --> R2
    E2 --> R3

    style CREATE fill:#e3f2fd
    style CLAIM fill:#e8f5e9
    style EXECUTE fill:#e8f5e9
    style RELEASE fill:#fff3e0
```

**When to use Tasks MCP**:

- Multi-session work (spans multiple conversations)
- Work with dependencies (blocked by / blocks)
- Strategic planning and tracking
- Discoverable by future sessions

## Core Functions

| Function                                           | Purpose                                                     |
| -------------------------------------------------- | ----------------------------------------------------------- |
| `mcp__pkb__create_task(title, ...)`                | Create new task                                             |
| `mcp__pkb__get_task(id)`                           | Get task details + relationship context                     |
| `mcp__pkb__update_task(id, updates={...})`         | Update non-terminal fields (priority, tags, assignee, body) |
| `mcp__pkb__release_task(id, status, summary, ...)` | Release task to handoff status with summary                 |
| `mcp__pkb__complete_task(id, completion_evidence)` | Mark task done with evidence (legacy path)                  |
| `mcp__pkb__list_tasks(status, ...)`                | List/filter tasks                                           |
| `mcp__pkb__task_search(query)`                     | Semantic search across tasks                                |
| `mcp__pkb__decompose_task(parent_id, subtasks)`    | Break down task into subtasks                               |

## Task Lifecycle

### State Machine

```
active → in_progress → merge_ready (PR filed) → done (after merge)
                     → done (non-code task completed)
                     → review (needs human attention)
                     → blocked (external dependency)
                     → cancelled (abandoned)
         ↕
      waiting (deferred for later)
```

### Claiming Tasks

Use `update_task` to claim:

```
update_task(id="<task-id>", updates={"status": "in_progress", "assignee": "polecat"})
```

### Releasing Tasks

Use `release_task` for all terminal/handoff transitions. Flat parameters — no nested objects:

```
release_task(id, status, summary, pr_url?, branch?, blocker?, reason?)
```

| Target Status | summary  | pr_url    | blocker   | reason    |
| ------------- | -------- | --------- | --------- | --------- |
| `merge_ready` | REQUIRED | soft-warn | -         | -         |
| `done`        | REQUIRED | optional  | -         | -         |
| `review`      | REQUIRED | -         | -         | soft-warn |
| `blocked`     | REQUIRED | -         | soft-warn | -         |
| `cancelled`   | REQUIRED | -         | -         | soft-warn |

`release_task` appends a timestamped evidence block to the task body, sets `released_at` in frontmatter, and records `pr_url`/`branch` if provided.

**Hard errors**: missing summary, unknown status, task already terminal (done/cancelled).

**Soft warnings**: context-specific fields missing (logged in response, tool still succeeds).

### Why `release_task` Instead of `update_task`

`update_task(updates={...})` requires a nested JSON object, which agents frequently serialize as a string instead of an object, drop fields on retry, or forget entirely. `release_task` uses flat string parameters and always requires a summary, making it harder to lose information than to capture it.

`update_task` remains for non-terminal field changes (priority, tags, assignee, body). It soft-hints toward `release_task` when a terminal status is detected.

### Canonical Statuses

| Status        | Meaning                                 | Terminal? |
| ------------- | --------------------------------------- | --------- |
| `active`      | Ready to be worked on                   | No        |
| `in_progress` | Currently being worked on               | No        |
| `merge_ready` | Work complete, PR filed, awaiting merge | No        |
| `review`      | Needs human/manager review              | No        |
| `blocked`     | Waiting on external dependency          | No        |
| `waiting`     | Deferred for later                      | No        |
| `draft`       | Early/incomplete/seed content           | No        |
| `done`        | Completed successfully                  | Yes       |
| `cancelled`   | Abandoned/no longer relevant            | Yes       |

Additional statuses exist (`paused`, `someday`, `submitted`, `accepted`) — see `graph.rs` for the full list and alias mappings.

## Multi-Project Organization

Tasks are organized by `project` field:

| Project   | Use For               |
| --------- | --------------------- |
| `aops`    | Framework tasks       |
| `writing` | Writing project tasks |
| (custom)  | Other projects        |

**Create with project**:

```python
mcp__pkb__create_task(
    title="Task title",
    type="task",
    project="aops",
    priority=2
)
```

## Dependencies

Tasks can depend on other tasks:

```python
# Create dependent task
mcp__pkb__create_task(
    title="Implement feature",
    depends_on=["task-id-of-prerequisite"]
)

# Check what's blocked
mcp__pkb__get_blocked_tasks()
```

## Graph Insertion Responsibility

**The creating agent is responsible for inserting tasks onto the work graph.**

Every task must be connected to the hierarchy:

```
task → epic → chain → project → strategic priority
```

When creating a task, the agent MUST:

1. **Identify the parent epic** - Search for existing epics in the project
2. **Link the task** - Use `depends_on` or wikilinks to connect to parent
3. **Create intermediates if needed** - If no suitable epic exists, create one that links to a project

**Why this matters:**

- Disconnected tasks become invisible to prioritization
- Orphaned work cannot be sequenced for delivery
- The task graph visualization reveals structural gaps

**Anti-pattern:** Creating standalone tasks without graph connections. If a task has no parent, it's not properly inserted.

```python
# WRONG: Orphaned task
mcp__pkb__create_task(
    title="Fix login bug",
    project="webapp"
)

# RIGHT: Connected to parent epic
mcp__pkb__create_task(
    title="Fix login bug",
    project="webapp",
    depends_on=["webapp-auth-epic"]  # Links to parent
)
```

## Task Assignment

Tasks can be assigned to a specific actor:

| Assignee | Meaning                                           |
| -------- | ------------------------------------------------- |
| `nic`    | Human tasks - requires judgment, external context |
| `bot`    | Agent tasks - automatable work                    |
| (unset)  | Available to anyone (legacy compatibility)        |

**Creating assigned tasks**:

```python
mcp__pkb__create_task(
    title="Review proposal",
    assignee="nic"  # Human task
)
```

**Listing tasks by assignee**:

```python
# Bot tasks
mcp__pkb__list_tasks(project="aops", assignee="bot")

# Human tasks
mcp__pkb__list_tasks(project="aops", assignee="nic")
```

## Task Storage

Tasks are stored as markdown files in `data/tasks/`:

- `data/tasks/inbox/` - New tasks
- `data/tasks/index.json` - Task index for fast queries
