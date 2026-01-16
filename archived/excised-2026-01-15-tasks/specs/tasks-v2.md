# Task System v2: Specification

> **Status**: APPROVED
> **Author**: Claude (with Nic)
> **Date**: 2026-01-12

## Executive Summary

Redesign the task system to support **hierarchical task decomposition** - breaking large goals ("write a book") into thousands of ordered, progressively deeper tasks over time. This is not subtask management; it's a tree-structured execution plan that grows organically.

### Core Principles

1. **Markdown is the source of truth** - Tasks remain human-readable files with rich context
2. **Graph-first relationships** - Dependencies, parent-child, and blocking are first-class
3. **Progressive decomposition** - Tasks split into children when ready, not all at once
4. **Subtasks become tasks** - No second-class citizens; everything is a node in the graph
5. **Index-accelerated queries** - JSON index rebuilt by cron; graph queries don't scan files

### Design Decisions (Resolved)

| Decision       | Choice                                                 |
| -------------- | ------------------------------------------------------ |
| File location  | Flat, grouped by project: `$ACA_DATA/<project>/tasks/` |
| Child ordering | Explicit `order` field in frontmatter                  |
| Auto-complete  | Not for MVP (explicit completion required)             |
| Type hierarchy | goal → project → task → action (semantic levels)       |
| Depth limits   | None (graph handles arbitrary depth)                   |

---

## 1. Task Model

### 1.1 Core Schema

Every task is a markdown file with YAML frontmatter:

```yaml
---
id: 20260112-write-book           # Unique identifier (date-slug)
title: Write a new book
type: goal                        # goal | project | task | action
status: active                    # inbox | active | blocked | waiting | done | cancelled
priority: 2                       # 0-4 (0=critical, 4=someday)
order: 0                          # Sibling ordering (lower = first)
created: 2026-01-12T10:00:00Z
modified: 2026-01-12T10:00:00Z

# Graph relationships
parent: null                      # Parent task ID (null = root)
depends_on: []                    # Must complete before this can start

# Decomposition metadata
depth: 0                          # Distance from root (0 = root goal)
leaf: true                        # True if no children (actionable)

# Optional fields
due: null
project: book                     # Project slug (also determines file location)
tags: []
effort: null                      # Estimated effort (hours, days, etc.)
context: null                     # @home, @computer, @errands, etc.
---

# Write a new book

## Context

I want to write a book about [topic]. This is a multi-year project...

## Observations

- [goal] This is the root goal for the book project

## Relations

- parent:: [[null]]
- children:: (none yet - needs decomposition)
```

### 1.2 Task Types (Semantic Levels)

| Type      | Description              | Typical Use                            |
| --------- | ------------------------ | -------------------------------------- |
| `goal`    | Multi-month/year outcome | "Write a book", "Get PhD"              |
| `project` | Coherent body of work    | "Complete manuscript", "Chapter 1"     |
| `task`    | Discrete deliverable     | "Write introduction", "Research topic" |
| `action`  | Single work session      | "Draft 500 words", "Email editor"      |

**Rule**: Only `leaf: true` tasks are directly actionable. Non-leaf tasks are containers.

### 1.3 Status Model

```
inbox → active → done
          ↓
       blocked ←→ waiting
          ↓
       cancelled
```

- **inbox**: Captured but not committed
- **active**: Currently workable (no blockers)
- **blocked**: Waiting on dependencies (`depends_on` not satisfied)
- **waiting**: Waiting on external input (person, event)
- **done**: Completed
- **cancelled**: Abandoned (preserved for history)

---

## 2. File Storage

### 2.1 Directory Structure

Tasks are stored flat within project directories:

```
$ACA_DATA/
├── book/
│   └── tasks/
│       ├── 20260112-write-book.md           # goal
│       ├── 20260112-complete-manuscript.md  # project
│       ├── 20260112-write-chapter-1.md      # project
│       ├── 20260112-ch1-outline.md          # action
│       ├── 20260112-ch1-draft.md            # action
│       └── 20260112-ch1-revise.md           # action
├── dissertation/
│   └── tasks/
│       └── ...
└── tasks/
    ├── index.json                           # Global index
    └── inbox/                               # Tasks without project
        └── 20260112-random-idea.md
```

### 2.2 Why Flat?

- **Graph defines hierarchy** - Parent/child in frontmatter, not folders
- **Simple file operations** - No nested folder management
- **Project grouping** - Natural namespace for related work
- **Easy backup/sync** - Git-friendly flat structure

---

## 3. Graph Relationships

### 3.1 Relationship Types

| Relationship | Stored In        | Computed                    |
| ------------ | ---------------- | --------------------------- |
| `parent`     | Task frontmatter | No                          |
| `children`   | Index            | Yes (inverse of parent)     |
| `depends_on` | Task frontmatter | No                          |
| `blocks`     | Index            | Yes (inverse of depends_on) |

### 3.2 Graph Queries

```python
# Decomposition tree
get_children(task_id) -> list[Task]      # Direct children
get_descendants(task_id) -> list[Task]   # All descendants (recursive)
get_ancestors(task_id) -> list[Task]     # Path to root
get_root(task_id) -> Task                # Root goal

# Dependency graph
get_dependencies(task_id) -> list[Task]  # What this depends on
get_dependents(task_id) -> list[Task]    # What depends on this (blocks)

# Actionability
get_ready() -> list[Task]                # Leaves with no unmet dependencies
get_blocked() -> list[Task]              # Tasks with unmet dependencies
get_next_actions(goal_id) -> list[Task]  # Ready leaves under a goal
```

### 3.3 Wikilinks Integration

Tasks can reference knowledge base notes:

```markdown
## Relations

- parent:: [[20260112-book-chapter-1]]
- depends_on:: [[20260110-research-topic]]
- related:: [[research/topic-notes]]
```

---

## 4. Task Decomposition Engine

### 4.1 Decomposition Model

Decomposition splits a task into children. It happens:

1. **On demand** - User or agent triggers decomposition
2. **Progressively** - Only decompose what's needed now
3. **With context** - Parent context flows to children

```
Goal: Write a book
  └── Project: Complete manuscript
        ├── Project: Write Chapter 1
        │     ├── Action: Outline chapter 1 [order=0]
        │     ├── Action: Write first draft [order=1, depends_on: outline]
        │     └── Action: Revise draft [order=2, depends_on: draft]
        ├── Project: Write Chapter 2 [order=1]
        │     └── (not yet decomposed)
        └── Project: Write Chapter 3 [order=2]
              └── (not yet decomposed)
```

### 4.2 Decomposition Rules

When decomposing a task:

1. **Create children as separate files** in same project directory
2. **Set parent reference** - Child points to parent ID
3. **Update parent** - Set `leaf: false`
4. **Set order** - Assign `order` values for sequencing
5. **Add dependencies** - Use `depends_on` for sequential steps

### 4.3 Decomposition Strategies

| Strategy       | Pattern                          | Example                              |
| -------------- | -------------------------------- | ------------------------------------ |
| **Sequential** | Each step depends on previous    | outline → draft → revise             |
| **Parallel**   | Independent siblings, same order | Ch1, Ch2, Ch3 (order=0,1,2, no deps) |
| **Phased**     | Groups with gate dependencies    | Draft phase → Review phase           |

### 4.4 MCP Tool

```python
decompose_task(
    task_id: str,
    children: list[dict],         # [{title, type, order, depends_on}, ...]
) -> list[Task]
```

**Example**:

```python
decompose_task("20260112-write-ch1", [
    {"title": "Outline chapter 1", "type": "action", "order": 0},
    {"title": "Write first draft", "type": "action", "order": 1,
     "depends_on": ["20260112-ch1-outline"]},
    {"title": "Revise draft", "type": "action", "order": 2,
     "depends_on": ["20260112-ch1-draft"]},
])
```

---

## 5. Subtasks Are Tasks

### 5.1 No Second-Class Citizens

Old model (deprecated):

```markdown
## Checklist

- [ ] Do thing 1
- [x] Do thing 2
```

New model: Each item is a full task file with `parent` relationship.

### 5.2 Display

When viewing a parent, children appear inline:

```
$ task show 20260112-write-ch1

Write Chapter 1 [project] [active]
├── [ ] Outline chapter 1 [action] [order=0]
├── [ ] Write first draft [action] [order=1] [blocked]
└── [ ] Revise draft [action] [order=2] [blocked]

Progress: 0/3 complete
Next action: Outline chapter 1
```

---

## 6. Index

### 6.1 Schema

```json
{
  "version": 2,
  "generated": "2026-01-12T10:00:00Z",
  "tasks": {
    "20260112-write-book": {
      "id": "20260112-write-book",
      "title": "Write a new book",
      "type": "goal",
      "status": "active",
      "order": 0,
      "parent": null,
      "children": ["20260112-complete-manuscript"],
      "depends_on": [],
      "blocks": [],
      "depth": 0,
      "leaf": false,
      "project": "book",
      "path": "book/tasks/20260112-write-book.md"
    }
  },
  "by_project": {
    "book": ["20260112-write-book", "20260112-complete-manuscript", ...]
  },
  "roots": ["20260112-write-book"],
  "ready": ["20260112-ch1-outline"],
  "blocked": ["20260112-ch1-draft", "20260112-ch1-revise"]
}
```

### 6.2 Rebuild

```bash
task index rebuild    # Full rebuild (cron)
task index update ID  # Incremental (after changes)
```

---

## 7. CLI & MCP Interface

### 7.1 CLI Commands

```bash
# Core
task add "Title" --type=task --project=book --parent=ID
task show ID
task done ID [ID2 ID3 ...]
task edit ID

# Graph queries
task ready [--project=book]      # Actionable tasks
task blocked                      # Blocked tasks
task tree ID                      # Decomposition tree
task deps ID                      # Dependency graph

# Decomposition
task decompose ID                 # Interactive decomposition
task reorder ID                   # Reorder children

# Index
task index rebuild
task index stats
```

### 7.2 MCP Tools

```python
# CRUD
create_task(title, type, project, parent, depends_on, order) -> Task
get_task(id) -> Task
update_task(id, **fields) -> Task
complete_task(id) -> Task

# Queries
get_ready_tasks(project=None) -> list[Task]
get_blocked_tasks() -> list[Task]
get_task_tree(id) -> TreeNode
get_children(id) -> list[Task]
get_dependencies(id) -> list[Task]

# Decomposition
decompose_task(id, children: list[dict]) -> list[Task]

# Bulk
complete_tasks(ids: list[str]) -> list[Task]
reorder_children(parent_id, order: list[str]) -> bool
```

---

## 8. Implementation Phases

### Phase 1: Core Model

- [ ] New Task model with graph fields + order
- [ ] Flat file storage in project directories
- [ ] Index schema v2
- [ ] Index rebuild script

### Phase 2: Graph Queries

- [ ] Parent/child traversal
- [ ] Dependency graph (depends_on/blocks)
- [ ] Ready/blocked computation
- [ ] Tree display

### Phase 3: CLI

- [ ] Basic commands (add, show, done, ready)
- [ ] Tree visualization
- [ ] Decompose command

### Phase 4: MCP Server

- [ ] All tools exposed via MCP
- [ ] Integration with Claude Code

---

## 9. Success Criteria

1. **"Write a book" decomposes to 100+ tasks** - Hierarchical decomposition works
2. **`task ready` shows actionable items** - Always know what to do next
3. **Completing actions updates tree** - Progress visible
4. **Agent can decompose via MCP** - Automation works
5. **Files remain human-readable** - Markdown preserved
6. **Queries are fast** - Index-based, sub-second

---

## Appendix: Example Tree

```
book/tasks/
├── 20260112-write-book.md           # goal, parent=null, leaf=false
├── 20260112-complete-manuscript.md  # project, parent=write-book
├── 20260112-write-ch1.md            # project, parent=manuscript, order=0
├── 20260112-ch1-outline.md          # action, parent=write-ch1, order=0, READY
├── 20260112-ch1-draft.md            # action, parent=write-ch1, order=1, depends_on=outline
├── 20260112-ch1-revise.md           # action, parent=write-ch1, order=2, depends_on=draft
├── 20260112-write-ch2.md            # project, parent=manuscript, order=1, leaf=true
└── 20260112-write-ch3.md            # project, parent=manuscript, order=2, leaf=true
```

**State**: Only `ch1-outline` is ready. Ch2/Ch3 not yet decomposed (still leaves).
