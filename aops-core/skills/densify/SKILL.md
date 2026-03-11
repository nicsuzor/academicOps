---
name: densify
type: skill
category: instruction
description: Iterative task graph densification — add dependency edges between related tasks to improve priority weighting and discoverability. Designed for short, repeated sessions.
triggers:
  - "densify tasks"
  - "densify graph"
  - "improve task relationships"
  - "add task dependencies"
  - "task graph densification"
modifies_files: false
needs_task: false
mode: execution
domain:
  - operations
  - knowledge-management
allowed-tools: mcp__pkb__search,mcp__pkb__task_search,mcp__pkb__get_task,mcp__pkb__update_task,mcp__pkb__list_tasks,mcp__pkb__pkb_context,mcp__pkb__get_network_metrics,mcp__pkb__pkb_orphans,AskUserQuestion
version: 1.0.0
permalink: skills-densify
---

# Densify

Add dependency edges between related tasks to improve priority weighting. The graph is sparse — most tasks are isolated leaves with no `depends_on` edges, which means `downstream_weight` (the strongest priority signal at 25% of focus score) is zero for ~95% of tasks.

Densification is **strategic enrichment**, not structural cleanup. For hierarchy fixes and orphan reparenting, use [[garden#reparent]].

> **Design principle**: The system will always have more tasks than capacity. The trick is not reducing tasks — it's making the graph express which tasks matter most by connecting them to what they unblock.

## Modes

### session [strategy] (default)

Run a bounded densification session. Cap: ~10 tasks, ~20 minutes.

**Strategies** (pass as argument, or rotate between sessions):

| Strategy               | What it targets                          | When to use                                                            |
| ---------------------- | ---------------------------------------- | ---------------------------------------------------------------------- |
| `high-priority-sparse` | P0/P1 ready tasks with zero `depends_on` | Default first strategy — highest-value tasks that the graph can't rank |
| `project-cluster`      | Ready tasks within one project           | When a project feels disorganised                                      |
| `neighbourhood-expand` | Neighbours of high-weight tasks          | When load-bearing tasks should have more dependents                    |
| `cross-project-bridge` | Tasks sharing tags across projects       | When projects feel siloed                                              |

#### Step 1: Select candidates (5 min)

**high-priority-sparse** (default):

```
list_tasks(status="ready", priority=0)  → check which have empty depends_on
list_tasks(status="ready", priority=1)  → same check
```

Select up to 10 tasks with zero dependency edges.

**project-cluster**:

```
list_tasks(status="ready", project="<project>")
```

For each pair of sibling tasks, ask: does one need the other done first? Would one inform the other?

**neighbourhood-expand**:

```
list_tasks(status="ready", limit=5)  → pick top by downstream_weight
pkb_context(id=<top_task>, hops=2)   → find nearby unlinked tasks
```

**cross-project-bridge**:

```
search(query="<theme from active project>", limit=10)
```

Look for tasks in different projects that should be linked via `soft_depends_on`.

#### Step 2: Enrich each candidate (15 min)

For each task, use `pkb_context(id)` and `search(query=<task title>)` to understand its neighbourhood. Check:

1. **Missing `depends_on`**: Does this task require another task to be done first? This is a hard blocking dependency — task literally cannot start until the other is done.
2. **Missing `soft_depends_on`**: Would completing another task make this one easier, better informed, or more impactful? This is an "unlocker" — not blocking, but enabling.
3. **Wrong parent**: Is it under the right epic? Defer to [[garden#reparent]] rules.
4. **Missing tags**: Would topic tags help future semantic search find this task alongside related ones?

**Do NOT change priorities.** Densification is about structure, not re-prioritising.

#### Step 3: Present proposals to user

For **obvious relationships** (clear blocking dependency, sibling tasks with logical ordering, tasks that explicitly reference each other), apply autonomously without asking.

For **ambiguous relationships** (soft vs hard dependency unclear, cross-project links, tasks that seem related but might not be), use `AskUserQuestion` to present as a reviewable batch. Aim for 5-10 proposals per batch:

```
Densification proposals (strategy: high-priority-sparse, batch 1/1):

1. "Refine benchmarking methodology" (P1, osb):
   → add depends_on: "Process Oversight Board receipts" (needs data from receipts)
   → add soft_depends_on: "Define knowledge work requirements" (methodology overlap)

2. "Capture live Claude hook logs" (P1, aops):
   → add depends_on: "Capture live Gemini hook logs" (same data collection sprint)

3. ...

Approve all / reject specific numbers / modify?
```

#### Step 4: Apply approved changes

```
update_task(id=<task_id>, depends_on=[...existing, new_dep_id])
update_task(id=<task_id>, soft_depends_on=[...existing, new_soft_dep_id])
```

Log: "Session <date>: +N depends_on, +N soft_depends_on edges added across N tasks"

#### Step 5: Verify

Check 2-3 modified tasks:

```
get_network_metrics(id=<task_that_gained_a_dependent>)
```

Confirm `downstream_weight` increased for tasks that now have something depending on them.

### scan

Report current graph density without making changes.

```
list_tasks(status="ready", limit=0)          → total count
pkb_orphans(types=["task"])                   → zero-edge count
list_tasks(status="ready", limit=10)          → top by downstream_weight
```

Report:

- Total ready tasks
- Tasks with zero edges (true orphans)
- Top 10 by downstream_weight (the "load-bearing" tasks)
- % of ready tasks with non-zero downstream_weight

### measure

Compare current metrics against a baseline. Look up the densify tracking task in PKB (search for "densify baseline" or "graph density tracking") to find the recorded baseline, then run `scan` and compare. Update the tracking task body with the latest measurements.

## Session Cadence

- Run every few hours during active work, or when switching contexts
- Each session: pick ONE strategy, process ~10 tasks
- Rotate strategies across sessions for balanced coverage
- Log results in the densify tracking task for longitudinal tracking

## What This Feeds Into

- **`downstream_weight`** in PKB server (PageRank-derived) — gains signal from new edges
- **`_importance_score`** in dashboard (`downstream_weight * 20`, capped at 200)
- **`focus_score`** (spec, not yet implemented) — `downstream_signal` is 25% of total weight
- **`list_tasks(status="ready")`** — already sorts by `priority + downstream_weight`

## Anti-patterns

- Processing all tasks in one session (cap at 10)
- Auto-deciding ambiguous dependencies without user approval (obvious ones are fine — see Step 3)
- Adding `depends_on` when `soft_depends_on` is more accurate (blocking vs. enabling)
- Creating new epics/tasks — focus on edges between _existing_ tasks
- Duplicating [[garden#reparent]] logic — defer hierarchy fixes to garden
- Changing priorities — that's a separate concern
- Using `pkb_context(hops=2)` on high-degree nodes — the result set explodes. Use `hops=1` for nodes with >10 connections, or switch to `project-cluster` strategy instead
