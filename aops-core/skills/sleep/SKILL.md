---
name: sleep
type: skill
category: operations
description: "Periodic consolidation agent — session backfill, episode replay, index refresh, staleness sweep, brain sync. Runs on GitHub Actions cron or manually via /sleep."
triggers:
  - "sleep cycle"
  - "consolidation"
  - "brain maintenance"
  - "session summary"
  - "generate insights"
  - "session insights"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Bash,Read,Write,Grep,Glob,mcp__pkb__search,mcp__pkb__pkb_orphans,mcp__pkb__create_memory,mcp__pkb__list_tasks,mcp__pkb__graph_stats,mcp__pkb__get_network_metrics,mcp__pkb__update_task,mcp__pkb__get_task,mcp__pkb__task_search,mcp__pkb__pkb_context,mcp__pkb__bulk_reparent,~~ai-assistant
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

| Phase | Name              | What it does                                                |
| ----- | ----------------- | ----------------------------------------------------------- |
| 0     | Graph Health      | Run `graph_stats` — baseline measurement for this cycle     |
| 1     | Session Backfill  | Process pending transcripts with Gemini (see Phase 1 below) |
| 2     | Episode Replay    | Scan recent activity, identify promotion candidates         |
| 3     | Index Refresh     | Update mechanical framework indices (`SKILLS.md`, etc.)     |
| 4     | Staleness Sweep   | Detect orphans, stale docs, under-specified tasks           |
| 4b    | Graph Maintenance | Densify, reparent, or connect — pick ONE strategy           |
| 5     | Brain Sync        | Commit and push `$ACA_DATA`; re-run `graph_stats`           |

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

- **`triage_tasks.py`**: Scans task files, flags under-specified tasks. Run via:
  `uv run python aops-core/skills/garden/scripts/triage_tasks.py $ACA_DATA --recursive --format json`
- **PKB orphan detection**: `mcp__pkb__pkb_orphans()`
- **Git log**: Recent commits, task changes since last cycle
- **Own judgment**: The agent reads flagged tasks and decides whether they genuinely need attention. The script is a starting point, not the final word.

## Phase 4b: Graph Maintenance

Each cycle, pick ONE strategy based on what graph_stats shows needs the most attention:

| Condition                     | Strategy            | Action                                              |
| ----------------------------- | ------------------- | --------------------------------------------------- |
| `disconnected_epics` > 10     | Connect epics       | Find natural project parents for disconnected epics |
| `projects_without_goals` > 10 | Connect projects    | Link projects to existing goals                     |
| `flat_tasks` > 100            | Reparent flat tasks | Find epic/project parents for orphaned tasks        |
| `orphan_count` > 20           | Fix orphans         | Connect or archive truly disconnected nodes         |
| All metrics healthy           | Densify edges       | Use densify strategies to add dependency edges      |

**Bounded effort**: Process at most 30 items per cycle. Quality over quantity.

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

## Phase 1: Session Backfill (Session Insights)

Analyze Claude session transcripts with Gemini Flash 2.0 to produce structured insights (summary, accomplishments, learnings, skill compliance). Outputs saved to `$ACA_DATA/../sessions/summaries/YYYYMMDD-{session_id}.json`.

### Find pending sessions

```bash
uv run python aops-core/skills/sleep/scripts/find_pending.py --limit 5
```

### For each pending session

1. **Locate transcript**: `$ACA_DATA/../sessions/claude/YYYYMMDD-{project}-{session_id}-*.md`
   - If missing, generate: `uv run python aops-core/scripts/transcript_push.py <session_path>`

2. **Prepare prompt**:

```bash
PROMPT=$(PYTHONPATH=aops-core uv run python \
    aops-core/skills/sleep/scripts/prepare_prompt.py "$TRANSCRIPT")
```

3. **Call Gemini** via `~~ai-assistant` with the prepared prompt + `@{transcript}` reference

4. **Parse and validate**:

```bash
echo "$GEMINI_RESPONSE" | PYTHONPATH=aops-core uv run python \
    aops-core/skills/sleep/scripts/process_response.py "$DATE" "$SESSION_ID"
```

5. **Merge insights**:

```bash
echo "$INSIGHTS_JSON" | PYTHONPATH=aops-core uv run python \
    aops-core/skills/sleep/scripts/merge_insights.py "$INSIGHTS_FILE"
```

6. **Sync to PKB**:

```python
mcp__pkb__create_memory(
    title=f"Session insights: {session_id}",
    body=f"{summary}\n\nAccomplishments: {accomplishments}\nLearnings: {learnings}",
    tags=["session-insights", f"session-{session_id}", project]
)
```

Do NOT overwrite existing insights without user confirmation. Process up to 5 sessions per cycle. Prompt template: `aops-core/specs/session-insights-prompt.md`.

## Architecture

```
templates/github-workflows/sleep-cycle.yml        ← workflow template (maintained in $AOPS)
$ACA_DATA/.github/workflows/sleep-cycle.yml       ← installed copy (runs the agent)
aops-core/skills/garden/scripts/triage_tasks.py   ← task quality tool (Phase 4)
aops-core/skills/sleep/scripts/                   ← session insights scripts (Phase 1)
```

The workflow uses `anthropics/claude-code-action` to launch an agent with a consolidation prompt. The agent has access to the brain repo and academicOps tools.
