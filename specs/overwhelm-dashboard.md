---
title: Overwhelm Dashboard
type: spec
status: active
tags: [spec, dashboard, tasks, fast-indexer]
created: 2026-01-21
---

# Overwhelm Dashboard

Single system for task visibility and cognitive load management.

## Architecture

```mermaid
graph TD
    subgraph "Indexing"
        A[fast-indexer<br>Rust binary]
        B[index.json]
    end

    subgraph "Data Sources"
        C[Task markdown files]
        D[Daily notes]
        E[R2 cross-machine prompts]
    end

    subgraph "Rendering"
        F[Streamlit dashboard]
        G[task-viz skill]
    end

    C --> A
    A --> B
    B --> F
    B --> G
    D --> F
    E --> F
```

## Core Problem

Task state is scattered and not visible where needed. User returns to terminal and can't remember what they were doing across multiple machines and projects.

## User Story

**As** an overwhelmed academic with ADHD,
**I want** one place that shows all my tasks and what I was working on,
**So that** I can recover context quickly and stay oriented.

## Components

### 1. fast-indexer (Rust)

Location: `aops/libs/fast-indexer`

High-performance task file scanner that generates `index.json`:

```bash
fast-indexer --tasks-dir $ACA_DATA/tasks --output index.json
```

**Output format**:
```json
{
  "generated": "2026-01-21T10:00:00Z",
  "total_tasks": 42,
  "tasks": [
    {
      "id": "aops-abc123",
      "title": "Task title",
      "status": "active",
      "priority": 2,
      "project": "aops",
      "parent": null,
      "depends_on": [],
      "due": "2026-01-25",
      "file": "aops/aops-abc123.md"
    }
  ],
  "ready": ["aops-abc123"],
  "blocked": []
}
```

**Consumers**:
- [[Task MCP server]] - `rebuild_index()` wraps fast-indexer
- [[Overwhelm dashboard]] - reads index.json directly
- [[task-viz]] - generates graph visualizations

### 2. Streamlit Dashboard

Location: `aops-core/skills/dashboard/`

Renders task state and session context. No LLM calls in render path.

**Invocation**:
```bash
cd $AOPS && uv run streamlit run skills/dashboard/dashboard.py
```

**Panels**:

| Panel | Purpose |
|-------|---------|
| NOW | Current focus from daily notes |
| Priority Tasks | P0/P1 tasks grouped by project |
| Blockers | Tasks with unmet dependencies |
| Done Today | Completed items |
| Active Sessions | Cross-machine context from R2 |

### 3. Data Flow

```
Task files ──> fast-indexer ──> index.json ──> Dashboard
                                    │
                                    └──> Task MCP server
                                    └──> task-viz
```

**Key principle**: Dashboard is pure rendering. All computation happens in fast-indexer or pre-computed synthesis.

## Design Principles

### Context Recovery, Not Decision Support

The dashboard answers:
- **What's running where?** - Multiple terminals, multiple projects
- **Where did I leave off?** - Per-project context recovery
- **What's the state of X?** - Quick status check

It does NOT try to:
- Recommend ONE thing to do
- Hide options or force single-focus mode
- Make decisions for the user

### Information Density

- Show top priorities with "X more" indicators
- Group by project for orientation
- LLM synthesis for human-readable summaries (pre-computed)

## Acceptance Criteria

- [ ] fast-indexer generates valid index.json from task files
- [ ] Dashboard renders index.json without errors
- [ ] Cross-machine prompts visible via R2 integration
- [ ] Mobile/tablet accessible via browser
- [ ] Graceful degradation when data sources unavailable

## Related

- [[aops-0a7f6861]] - EPIC: fast-indexer adoption
- [[Task MCP server]] - Primary task operations interface
- [[task-viz]] - Network graph visualization
