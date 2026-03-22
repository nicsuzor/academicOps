---
name: sleep
type: skill
category: operations
description: "Periodic consolidation agent — session backfill, episode replay, index refresh, staleness sweep, brain sync. Runs on GitHub Actions cron or manually via /sleep."
triggers:
  - "sleep cycle"
  - "consolidation"
  - "brain maintenance"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Bash,Read,Write,Grep,Glob,mcp__pkb__search,mcp__pkb__pkb_orphans,mcp__pkb__create_memory,mcp__pkb__list_tasks,mcp__pkb__graph_stats,mcp__pkb__get_network_metrics,mcp__pkb__update_task,mcp__pkb__get_task,mcp__pkb__task_search,mcp__pkb__pkb_context,mcp__pkb__bulk_reparent
version: 0.1.0
tags:
  - consolidation
  - memory
  - cron
---

# Sleep Cycle: Periodic Consolidation

> **Taxonomy note**: This skill orchestrates periodic offline consolidation — transforming write-optimised storage (tasks, session logs) into read-optimised knowledge that agents actually use. See `specs/sleep-cycle.md` for full design rationale.

## How It Works

The sleep cycle is an **agent session**, not a script. A Claude agent is launched (via GitHub Actions cron or manually) with a consolidation prompt. The agent works through phases using judgment, calling tools as signals — not deterministic code that makes the decisions.

```bash
# Trigger via GitHub Actions (runs in $ACA_DATA repo)
gh workflow run sleep-cycle -R nicsuzor/brain

# Manual invocation as a skill
/sleep

# Focus on a specific area
gh workflow run sleep-cycle -R nicsuzor/brain -f focus="staleness only"
```

## Phases

The agent works through these in order, using judgment about what needs attention:

| Phase | Name              | What it does                                            |
| ----- | ----------------- | ------------------------------------------------------- |
| 0     | Graph Health      | Run `graph_stats` — baseline measurement for this cycle |
| 1     | Session Backfill  | Run `/session-insights batch` for pending transcripts   |
| 2     | Episode Replay    | Scan recent activity, identify promotion candidates     |
| 3     | Index Refresh     | Update mechanical framework indices (`SKILLS.md`, etc.) |
| 4     | Staleness Sweep   | Detect orphans, stale docs, under-specified tasks       |
| 4b    | Graph Maintenance | Densify, reparent, or connect — pick ONE strategy       |
| 5     | Brain Sync        | Commit and push `$ACA_DATA`; re-run `graph_stats`       |

## Phase 0: Graph Health Baseline

Run `graph_stats` at the start of every cycle. Record:

- `flat_tasks` — tasks with no parent or children
- `disconnected_epics` — epics not connected to a project/goal
- `projects_without_goals` — projects with no goal parent
- `orphan_count` — truly disconnected nodes
- `stale_count` — tasks not modified in 7+ days while in_progress

This is the baseline. Phase 5 re-runs graph_stats to measure what changed.

## Phase 4: Tools Available

The agent uses these as **signals**, not as deterministic verdicts:

- **PKB orphan detection**: `mcp__pkb__pkb_orphans()`
- **Git log**: Recent commits, task changes since last cycle
- **Own judgment**: The agent reads flagged tasks and decides whether they genuinely need attention.

## Phase 4b: Graph Maintenance

**Delegates to the Planner agent's `maintain` mode.** Sleep selects the strategy based on graph_stats; Planner executes it.

Each cycle, pick ONE strategy based on what graph_stats shows needs the most attention:

| Condition                     | Strategy            | Planner Activity                                       |
| ----------------------------- | ------------------- | ------------------------------------------------------ |
| `disconnected_epics` > 10     | Connect epics       | Reparent — find project parents for disconnected epics |
| `projects_without_goals` > 10 | Connect projects    | Reparent — link projects to existing goals             |
| `flat_tasks` > 100            | Reparent flat tasks | Reparent — find epic/project parents for orphans       |
| `orphan_count` > 20           | Fix orphans         | Reparent — connect or archive disconnected nodes       |
| All metrics healthy           | Densify edges       | Densify — use strategies to add dependency edges       |

See `aops-core/skills/planner/SKILL.md` → `maintain` mode for full activity reference.

**Bounded effort**: Process at most 100 items per cycle. Use `mcp__pkb__bulk_reparent` for efficiency when processing multiple items with the same parent. Quality over quantity.

**Autonomous vs. flagged**:

- **Obvious**: Task title mentions the project/epic by name → reparent autonomously
- **Ambiguous**: Flag for user review in the cycle log, don't apply

**Measure after**: Re-run `graph_stats` in Phase 5 to confirm the metric improved.

## Active Loop Integration

When running via `/loop` or `/active-loop`, the sleep cycle follows the active-loop protocol:

1. Read the DRAFT PR body for prior cycle learnings
2. Use the "Next" field from the last cycle to inform this cycle's Phase 4b strategy
3. After Phase 5, update the PR body with the cycle log entry

## Design Principles

1. **Smart agents, not dumb code** — tools provide signals; the agent decides
2. **Idempotent** — running twice produces the same result
3. **Incremental** — only processes what's new since last run
4. **Surfaces, doesn't decide** — flags candidates for human/supervised review
5. **No moldy docs** — never creates knowledge docs without a named consumer

## Architecture

```
templates/github-workflows/sleep-cycle.yml   ← workflow template (maintained in $AOPS)
$ACA_DATA/.github/workflows/sleep-cycle.yml  ← installed copy (runs the agent)
```

The workflow uses `anthropics/claude-code-action` to launch an agent with a consolidation prompt. The agent has access to the brain repo and academicOps tools.
