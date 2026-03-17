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
allowed-tools: Bash,Read,Write,Grep,Glob,mcp__pkb__search,mcp__pkb__pkb_orphans,mcp__pkb__create_memory,mcp__pkb__list_tasks
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

| Phase | Name             | What it does                                            |
| ----- | ---------------- | ------------------------------------------------------- |
| 1     | Session Backfill | Run `/session-insights batch` for pending transcripts   |
| 2     | Episode Replay   | Scan recent activity, identify promotion candidates     |
| 3     | Index Refresh    | Update mechanical framework indices (`SKILLS.md`, etc.) |
| 4     | Staleness Sweep  | Detect orphans, stale docs, under-specified tasks       |
| 5     | Brain Sync       | Commit and push `$ACA_DATA`                             |

## Phase 4: Tools Available

The agent uses these as **signals**, not as deterministic verdicts:

- **`triage_tasks.py`**: Scans task files, flags under-specified tasks. Run via:
  `uv run python aops-core/skills/garden/scripts/triage_tasks.py $ACA_DATA --recursive --format json`
- **PKB orphan detection**: `mcp__pkb__pkb_orphans()`
- **Git log**: Recent commits, task changes since last cycle
- **Own judgment**: The agent reads flagged tasks and decides whether they genuinely need attention. The script is a starting point, not the final word.

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
aops-core/skills/garden/scripts/triage_tasks.py  ← task quality tool (one signal among many)
```

The workflow uses `anthropics/claude-code-action` to launch an agent with a consolidation prompt. The agent has access to the brain repo and academicOps tools.
