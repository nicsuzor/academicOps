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
allowed-tools: Bash,Read,Write,Grep,Glob,mcp__pkb__search,mcp__pkb__pkb_orphans,mcp__pkb__create_memory,mcp__pkb__list_tasks,mcp__pkb__graph_stats,mcp__pkb__get_network_metrics,mcp__pkb__update_task,mcp__pkb__get_task,mcp__pkb__task_search,mcp__pkb__pkb_context,mcp__pkb__bulk_reparent,mcp__pkb__find_duplicates,mcp__pkb__batch_merge,mcp__pkb__merge_node,mcp__pkb__complete_task,mcp__pkb__batch_reclassify,mcp__pkb__batch_archive,mcp__pkb__batch_update,mcp__omcp__messages_search,mcp__omcp__messages_query,mcp__omcp__calendar_list_events
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

| Phase | Name                        | What it does                                            |
| ----- | --------------------------- | ------------------------------------------------------- |
| 0     | Graph Health                | Run `graph_stats` — baseline measurement for this cycle |
| 1     | Session Backfill            | Run `/session-insights batch` for pending transcripts   |
| 2     | Episode Replay              | Scan recent activity, identify promotion candidates     |
| 3     | Index Refresh               | Update mechanical framework indices (`SKILLS.md`, etc.) |
| 4     | Data Quality Reconciliation | Dedup, staleness verification, misclassification        |
| 5     | Staleness Sweep             | Detect orphans, stale docs, under-specified tasks       |
| 5b    | Graph Maintenance           | Densify, reparent, or connect — pick ONE strategy       |
| 6     | Brain Sync                  | Commit and push `$ACA_DATA`; re-run `graph_stats`       |

## Phase 0: Graph Health Baseline

Run `graph_stats` at the start of every cycle. Record:

- `flat_tasks` — tasks with no parent or children
- `disconnected_epics` — epics not connected to a project
- `projects_without_goal_linkage` — projects with no `goals: []` field populated
- `orphan_count` — truly disconnected nodes
- `stale_count` — tasks not modified in 7+ days while in_progress

This is the baseline. Phase 6 re-runs graph_stats to measure what changed.

## Phase 4: Data Quality Reconciliation

Before structural work, fix the data. Structural metrics are meaningless when the graph is inflated with duplicates, stale items, and misclassified content. Data quality MUST run before Graph Maintenance (Phase 5b).

Three activities, run in order. Each is bounded per cycle.

### Activity 1: Deduplication (mechanical, autonomous)

1. Run `find_duplicates(mode="both")` to get clusters by title + semantic similarity.
2. For high-confidence clusters: merge autonomously via `batch_merge`. The tool selects the canonical node (most connected, most content).
3. For ambiguous clusters: log in cycle summary for human review. Don't merge.
4. Batch limit: up to 50 merges per cycle.

### Activity 2: Staleness Verification (evidence-based)

Target: active tasks with age >= 90 days.

For each candidate (up to 20 per cycle):

1. Read the task body for context (action required, deadline, email reference).
2. Search for completion evidence:
   - Sent email matching task subject/keywords (`messages_search`)
   - Calendar events matching task context (`calendar_list_events`)
   - Git commits referencing the task
3. Decision:
   - Evidence of completion found → `complete_task` with note explaining evidence
   - Deadline >90d past + zero evidence of any activity → `complete_task` with "auto-closed: no activity, deadline long past"
   - Genuinely ambiguous (some activity but unclear completion) → flag in cycle summary

**Environment guard**: Email/calendar tools require local MCP servers (not available on GitHub Actions). When running on CI, skip evidence-based verification entirely — only flag candidates. Staleness verification only runs effectively during manual `/sleep` invocations on the Mac.

### Activity 3: Misclassification Detection (pattern-based)

Target patterns:

- Tasks with "Email:" title prefix + age >60d + no children → likely untriaged email captures
- Tasks age >180d + no children + sparse body → likely fragments never triaged
- Tasks whose body is purely informational (no action items)

For matches:

- Clear non-tasks → `batch_archive` with reason, or `batch_reclassify` to "memory"
- Ambiguous → flag in cycle summary
- Batch limit: up to 30 per cycle.

**Time budget**: Phase 4 gets 10 minutes max. Exit the phase when time is up.

## Phase 5: Tools Available

The agent uses these as **signals**, not as deterministic verdicts:

- **PKB orphan detection**: `mcp__pkb__pkb_orphans()`
- **Git log**: Recent commits, task changes since last cycle
- **Own judgment**: The agent reads flagged tasks and decides whether they genuinely need attention.

## Phase 5b: Graph Maintenance

**Delegates to the Planner agent's `maintain` mode.** Sleep selects the strategy based on graph_stats; Planner executes it.

Each cycle, pick ONE strategy based on what graph_stats shows needs the most attention:

| Condition                            | Strategy            | Planner Activity                                                              |
| ------------------------------------ | ------------------- | ----------------------------------------------------------------------------- |
| `disconnected_epics` > 10            | Connect epics       | Reparent — find project parents for disconnected epics                        |
| `projects_without_goal_linkage` > 10 | Link projects       | Add `goals: []` metadata — link projects to existing goals via metadata field |
| `flat_tasks` > 100                   | Reparent flat tasks | Reparent — find epic/project parents for orphans                              |
| `orphan_count` > 20                  | Fix orphans         | Reparent — connect or archive disconnected nodes                              |
| All metrics healthy                  | Densify edges       | Densify — use strategies to add dependency edges                              |

**Type-aware orphan detection**: `pkb_orphans` now reports both missing-parent AND wrong-type-parent orphans (e.g., a task parented directly to a project instead of an epic). Phase 5b should treat wrong-type-parent orphans the same as missing-parent orphans when selecting a reparent strategy.

See `aops-core/skills/planner/SKILL.md` → `maintain` mode for full activity reference.

**Bounded effort**: Process a configurable number of items per cycle (default 100, set via `batch_limit` workflow input). Use `mcp__pkb__bulk_reparent` for efficiency when processing multiple items with the same parent. Quality over quantity.

**Autonomous vs. flagged**:

- **Obvious**: Task title mentions the project/epic by name → reparent autonomously
- **Ambiguous**: Flag for user review in the cycle log, don't apply

**Measure after**: Re-run `graph_stats` in Phase 6 to confirm the metric improved.

## Active Loop Integration

When running via `/loop` or `/active-loop`, the sleep cycle follows the active-loop protocol:

1. Read the DRAFT PR body for prior cycle learnings
2. Use the "Next" field from the last cycle to inform this cycle's Phase 5b strategy
3. After Phase 6, update the PR body with the cycle log entry

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
