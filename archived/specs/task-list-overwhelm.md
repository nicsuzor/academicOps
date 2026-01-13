---
title: Task State Index
type: spec
category: spec
status: in-progress
permalink: task-state-index
tags: [spec, tasks, foundation]
alias: [overwhelm, task-index]
---

# Task State Index

**Status**: In Progress

## Workflow

```mermaid
graph TD
    subgraph "Writers"
        A[email skill]
        B[session-insights]
        C[tasks skill]
        D[daily file]
    end

    subgraph "Index"
        E[regenerate_task_index.py]
        F[index.json]
        G[INDEX.md - derived]
    end

    subgraph "Readers"
        H[Dashboard]
        I[task-viz]
        J[daily file]
        K[/tasks command]
    end

    subgraph "Synthesis"
        L[synthesize_dashboard.py]
        M[synthesis.json]
    end

    A --> E
    B --> E
    C --> E
    D --> E
    E --> F
    F --> G
    F --> H
    F --> I
    F --> J
    F --> K
    F --> L
    L --> M
    M --> H
```

This spec is responsible for the task state index:

- The canonical, always-current source of task state
- Everything else reads from this
- Only written to as defined by this spec
- Located at `$ACA_DATA/tasks/index.json`

## User Story

**As** Nic (overwhelmed academic with ADHD),
**I want** one place that knows what all my tasks are and what state they're in,
**So that** I can trust it and build views/automations on top of it.

## The Core Problem

Task state is scattered, stale, and not visible where I need it. Individual task files exist but there's no reliable index that:

- Knows all tasks
- Tracks current state (priority, project, due, progress)
- Gets updated by ingest sources
- Feeds display surfaces

## Task state

### Index Structure (JSON)

```json
{
  "generated": "2025-12-25T10:00:00Z",
  "total_tasks": 42,
  "tasks": [
    {
      "slug": "tja-revisions",
      "title": "TJA paper revisions",
      "status": "active",
      "priority": 0,
      "project": "tja",
      "due": "2025-01-15",
      "source": "manual",
      "subtasks_total": 5,
      "subtasks_done": 2,
      "last_activity": "2025-12-24",
      "file": "active/tja-revisions.md"
    }
  ],
  "priority_by_project": {
    "tja": ["tja-revisions", "tja-data-check"],
    "uncategorized": ["misc-task"]
  },
  "priority_by_due": {
    "overdue": [],
    "this_week": ["tja-revisions"],
    "next_week": [],
    "later": ["tja-data-check"],
    "no_date": ["misc-task"]
  }
}
```

### Why JSON

- Machine-readable for [[Cognitive Load Dashboard Spec]], [[task-viz]], scripts
- Single source of truth for all consumers
- Fast to parse, easy to query

### Human View (Derived)

`$ACA_DATA/tasks/INDEX.md` is regenerated from JSON for Obsidian browsing. Not the source of truth.

### Task File Schema (Required Fields)

```yaml
---
title: Task title
type: task
status: active|waiting|done|archived
priority: P0|P1|P2|P3
project: project-slug  # required, use 'uncategorized' if none
due: YYYY-MM-DD        # optional
source: email|transcript|manual|implied
subtasks:              # optional, list of checklist items
---
```

## Features That Write to Index

| Feature                      | What it writes                               | Spec        |
| ---------------------------- | -------------------------------------------- | ----------- |
| [[email]] skill              | New tasks from emails                        | (exists)    |
| [[skills/session-insights/]] | Activity updates, new tasks from transcripts | (exists)    |
| [[tasks]] skill              | Manual task creation/updates                 | (exists)    |
| [[daily]] file               | Priority changes, progress updates           | (to define) |

## Features That Read from Index

| Feature          | What it reads                           | Current State                                      |
| ---------------- | --------------------------------------- | -------------------------------------------------- |
| [[dashboard]]    | Grouped/sorted task list, progress bars | Reads task files directly via `load_focus_tasks()` |
| [[task-viz]]     | Task graph data                         | Reads task files directly                          |
| [[daily]] file   | Today's priorities, what to work on     | (to define)                                        |
| `/tasks` command | CLI task list                           | Reads task files directly                          |

**Note**: Consumers currently read task files directly. `index.json` is an optimization that provides:

- Faster queries (no file I/O per request)
- Pre-computed groupings (by project, priority, due date)
- Validation layer (catches missing required fields)

## Acceptance Criteria

- [x] **AC1**: `index.json` reflects current state of all task files
- [x] **AC2**: Tasks missing required fields are flagged (validation on regenerate)
- [x] **AC3**: User can answer "what are my tasks?" from index alone
- [x] **AC4**: Consumers can optionally read from `index.json` for better performance
- [ ] **AC5**: Cron job runs every 5 minutes (not yet configured)
- [x] **AC6**: LLM synthesis combines data sources into actionable guidance
- [x] **AC7**: Dashboard shows synthesis panel when fresh (<10 min), falls back to basic view

## Implementation

### Task Index

Script: `$AOPS/scripts/regenerate_task_index.py`

1. Glob all `$ACA_DATA/tasks/**/*.md` (excluding INDEX.md)
2. Parse frontmatter, count subtask checkboxes
3. Build JSON structure with groupings
4. Write `index.json` (primary) + `INDEX.md` (derived)

**Trigger**: Cron every 5 min (simple, reliable, no daemon needed)

### LLM Synthesis

Script: `$AOPS/scripts/synthesize_dashboard.py`

Combines multiple data sources to answer the overwhelm questions:

- **What should I be doing?** → P0/P1 tasks from `index.json`
- **What did I accomplish?** → Checked items from `daily.md`
- **What am I waiting on?** → Tasks with `status: waiting`
- **Where was I working?** → Recent prompts from Cloudflare R2

Calls Claude API to synthesize into structured JSON:

```json
{
  "accomplishments": { "count": 8, "summary": "...", "highlight": "..." },
  "alignment": { "status": "on_track|drifted|blocked", "note": "..." },
  "next_action": { "task": "...", "reason": "...", "project": "..." },
  "context": { "last_machine": "...", "recent_threads": ["...", "..."] },
  "waiting_on": [{ "task": "...", "blocker": "..." }],
  "suggestion": "..."
}
```

**Output**: `$ACA_DATA/dashboard/synthesis.json`

**Trigger**: Manual or cron (same schedule as index)

### Dashboard Rendering

The [[Cognitive Load Dashboard Spec]] renders synthesis.json if fresh (<10 min old):

- **🧠 FOCUS SYNTHESIS** panel with next action prominent
- Grid of cards: Done, Alignment, Context, Blocked
- Optional suggestion footer

Falls back to basic "What Now?" panel (P0/P1 task list) if synthesis is stale.

**Migration**: Deprecates `data/assets/current_view.json` - that becomes `$ACA_DATA/tasks/index.json`
