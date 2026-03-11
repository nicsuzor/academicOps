---
title: Intentions
type: spec
status: active
tier: ux
depends_on: [task-focus-scoring, effectual-planning-agent]
tags: [spec, ux, intentions, focus]
---

# Intentions

## Giving Effect

- [[aops-core/commands/intend.md]] — `/intend` command for declaring, listing, and completing intentions
- [[aops-core/skills/daily/instructions/focus-and-recommendations.md]] — Intention-organized Focus section
- [[aops-core/skills/daily/instructions/reflect.md]] — End-of-day and weekly reflection (part of `/daily`)
- [[aops-core/commands/pull.md]] — Intention-scoped task pulling
- [[task-focus-scoring.md]] — `intention_alignment` signal (highest weight)
- `$ACA_DATA/intentions.yaml` — Active intention state file

## Problem

The framework currently presents an undifferentiated queue of hundreds of tasks. The system knows about priority, downstream weight, project activity — but it doesn't know what the user **intends to accomplish**. The user's actual working mode is: "I intend to get X out." Everything should flow from that declaration.

Without intentions, the system offers:

- 500+ tasks with no principled way to scope the view
- Daily notes that recommend tasks across all projects equally
- `/pull` that selects from the global ready queue
- Dashboard that shows the full graph (overwhelming for ADHD brain)
- Agents that pull whatever's highest-priority, regardless of what the human is focused on

The core insight from comparing with intention-based systems: **choosing what matters is the first act, not the last.** The system should ask "what do you intend to accomplish?" before it asks "what should you do next?"

## Core Concept

An **intention** is a declaration of focus on an existing PKB node (goal, project, or epic). It is NOT a new document type. It is a pointer from the user's current working scope to an existing node in the task graph.

"I intend to get the OSB benchmarking study out" → links to the existing `osb-benchmarking` project node → everything downstream (daily note, dashboard, `/pull`, agents) filters to that subgraph.

### Design Principles

1. **Simplicity of entry.** Declaring an intention is one command: `/intend "get the OSB study out"`. The system does the PKB search, confirmation, and decomposition offer.

2. **Focus over exhaustiveness.** When intentions are active, the system shows the intention subgraph — not 547 tasks. Items outside intentions still surface when urgent, but they're secondary.

3. **Reflection as first-class.** Intentions create a natural frame for end-of-day and weekly reflection: "Did this intention get the attention it deserved? Is it still the right intention?"

4. **Backward compatible.** When no intentions are active, all commands fall back to current behaviour. Intentions are a progressive enhancement, not a breaking change.

5. **Lightweight state.** Intentions are stored in a simple YAML file, not as PKB documents. They add no noise to the task graph. They're a lens on the graph, not part of it.

## Data Model

### Active Intentions State

Stored in `$ACA_DATA/intentions.yaml`:

```yaml
version: 1
active:
  - root_id: "osb-benchmarking-abc123"
    declared: "2026-03-10T09:00:00+10:00"
    label: "Get the OSB benchmarking study out"
  - root_id: "aops-intentions-def456"
    declared: "2026-03-10T09:15:00+10:00"
    label: "Ship the intentions feature"
max_active: 3
```

**File-level fields:**

| Field        | Type | Description                                                |
| ------------ | ---- | ---------------------------------------------------------- |
| `max_active` | int  | Configurable upper bound on active intentions (default: 3) |

**Per-intention entry fields:**

| Field      | Type     | Description                                   |
| ---------- | -------- | --------------------------------------------- |
| `root_id`  | string   | PKB node ID (goal, project, or epic)          |
| `declared` | ISO 8601 | When the intention was declared               |
| `label`    | string   | Human-readable snapshot of what the user said |

The file is checked in to `$ACA_DATA` and persists across sessions.

### Intention Subgraph

The **intention subgraph** for a given root node is computed at query time (never stored):

1. **Descendants**: All children of the root node recursively (via `get_task_children(id, recursive=True)`)
2. **Dependency frontier**: Tasks outside the descendant set that descendants have `depends_on` relationships with
3. **Ancestor breadcrumb**: The root node's parent chain up to the goal level (for context display)

The subgraph is the scope for:

- Focus scoring (`intention_alignment` signal)
- `/pull` task selection
- Daily note "Next actions" per intention
- Dashboard graph filtering
- Agent dispatch (swarm scope)

### Subgraph Statistics

For display and triage, compute per intention:

| Stat           | Description                                    |
| -------------- | ---------------------------------------------- |
| `total`        | Total tasks in descendant set                  |
| `done`         | Completed tasks                                |
| `ready`        | Leaf tasks with active status and all deps met |
| `blocked`      | Tasks with unmet dependencies                  |
| `in_progress`  | Tasks currently being worked on                |
| `progress_pct` | `done / total * 100` (0 if `total` is 0)       |
| `next_task`    | Highest-priority ready task                    |

## Lifecycle

### Declaration

User runs `/intend "description"`. The system:

1. Searches PKB for matching goal/project/epic
2. Presents candidates with breadcrumb and child count
3. User confirms which node
4. If root has no leaf tasks, offers effectual planner decomposition
5. Writes to `$ACA_DATA/intentions.yaml`
6. Reports subgraph stats

### Active

While an intention is active:

- Focus scoring boosts its subgraph tasks (highest-weight signal)
- Daily note leads with intention progress and next actions
- `/pull` selects from intention subgraphs by default
- Dashboard highlights the intention subgraph
- Automated agents scope to intention subgraphs

### Completion

User runs `/intend done "label"`. The system:

1. Triggers end-of-intention reflection (progress summary, lessons)
2. Removes from `$ACA_DATA/intentions.yaml`
3. Offers to declare a replacement intention

### Staleness

If an intention has no completed tasks in 7+ days, it's flagged during daily note and `/reflect` as potentially stale. The user is prompted: "Still the right intention, or has focus shifted?"

## Integration Points

### Focus Scoring

New signal `intention_alignment` (see [[task-focus-scoring.md]]):

| Signal                | Range   | Description                                                                                                 |
| --------------------- | ------- | ----------------------------------------------------------------------------------------------------------- |
| `intention_alignment` | 0.0-1.0 | 1.0 if task is in any active intention's subgraph. 0.2 if same project but outside subgraph. 0.0 otherwise. |

Default weight: 0.30 (strongest signal). When no intentions are active, `intention_alignment` is 0.0 for all tasks and the remaining signals determine ranking naturally — the full 7-weight formula still applies.

### Daily Note

When intentions are active, the Focus section reorganizes around intentions (see [[focus-and-recommendations.md]]):

- Lead with intention status (progress bar, ready/blocked counts)
- "Next actions" per intention (replaces SHOULD/DEEP/ENJOY/QUICK/UNBLOCK)
- "Outside Intentions" section catches urgent items not in any subgraph

When no intentions are active, fall back to current category-based recommendations.

### `/pull` Command

Default behaviour changes when intentions are active:

- Filter ready tasks to union of intention subgraphs
- Present selected task with intention context
- Override with `/pull --all` for global ready queue

### Effectual Planner

When `/intend` links to a node with no leaf tasks:

- Trigger Mode 2 (DOWN — Epic Decomposition)
- Planner decomposes into actionable tasks
- Report subgraph stats after decomposition

### Dashboard

When intentions are active:

- Sidebar shows intention selector
- Spotlight shows intention progress (not dynamically-selected epic)
- Task graph dims non-intention nodes (not removed — spatial context preserved)
- "All Work" toggle returns to full graph

### Agent Dispatch

When intentions are active:

- `polecat swarm` defaults to intention subgraph scope
- Override with `--all` flag
- SessionStart context injection includes intention summary

## Reflection

Intentions create a natural frame for structured reflection:

### End-of-day

Triggered by "reflect", "end of day", etc. — handled within `/daily`. Per active intention:

1. Progress delta (tasks completed today, % change)
2. Next actions for tomorrow
3. "Did this intention get the attention it deserved?" (yes/some/no)
4. "Still the right intention?"

For unplanned work:

1. Tasks completed outside any intention
2. "Should any of this become an intention?"

### Weekly

1. Per-intention progress over the week
2. Time allocation (sessions per intention vs. outside)
3. "Are these still the right intentions for next week?"
4. Archive completed intentions, declare new ones

## Open Questions

1. **Intention granularity.** Should intentions point only to goals/projects/epics, or also to individual tasks? Current design restricts to goal/project/epic to ensure a meaningful subgraph. Individual task focus is handled by `/pull`.

2. **Cross-intention dependencies.** When Task A (intention 1) depends on Task B (intention 2), the dependency frontier includes B. Is this sufficient, or do we need explicit cross-intention visibility?

3. **Intention history.** Should completed intentions be archived with their reflection notes? Proposed: yes, append to `$ACA_DATA/intentions-archive.yaml` for weekly/monthly review.

4. **Daily skill alignment** (from [[effectual-planning-agent.md]] open question #5): This spec resolves the tension between operational heuristics (SHOULD/DEEP/etc.) and information-value prioritisation. When intentions are active, task selection is intention-scoped; within that scope, the agent still applies judgment about what advances the intention most.
