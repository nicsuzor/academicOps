---
title: Supervisor Architecture
type: spec
description: Unified specification for task supervision — parallel swarm dispatch and iterative burst orchestration
status: active
tier: polecat
depends_on: [polecat-system]
supersedes: [polecat-supervision, polecat-swarms, worker-hypervisor]
tags: [spec, polecat, architecture, supervisor]
created: 2026-03-11
implements:
  - swarm-supervisor skill
  - burst-supervisor skill
  - polecat/supervisor_loop.py
  - polecat/swarm.py
  - polecat/engineer.py
---

# Supervisor Architecture

Unified specification for task supervision. All orchestration patterns — parallel swarm, iterative burst, and the deprecated hypervisor — are instances of one abstraction: **a supervisor that creates or selects tasks, dispatches them to workers, and evaluates results.**

## Giving Effect

- [[polecat/supervisor_loop.py]] — LLM-driven parallel dispatch (swarm mode)
- [[polecat/swarm.py]] — Multiprocessing worker pool
- [[polecat/engineer.py]] — Refinery merge queue processor
- [[polecat/manager.py]] — Worktree lifecycle, atomic task claiming
- [[skills/swarm-supervisor/SKILL.md]] — Full lifecycle orchestration skill (swarm mode)
- [[skills/burst-supervisor/SKILL.md]] — Iterative long-running orchestration skill (burst mode)
- [[WORKERS.md]] — Worker registry (types, capabilities, selection rules)
- [[LIFECYCLE-HOOKS.md]] — Trigger hooks (queue-drain, stale-check, post-finish)

## Core Abstraction

Every supervisor instance has four concerns:

| Concern      | What it does                                 | Who decides           |
| ------------ | -------------------------------------------- | --------------------- |
| **Select**   | Choose which tasks to work on next           | Agent (LLM judgment)  |
| **Dispatch** | Send tasks to workers                        | `polecat run -t <id>` |
| **Evaluate** | Judge whether worker output is acceptable    | Agent (LLM judgment)  |
| **Persist**  | Record state for recovery across invocations | Task body (PKB)       |

The two modes differ in how they combine these concerns:

```
SWARM MODE                          BURST MODE
(parallel, fire-and-forget)         (iterative, evaluate-and-revise)

Select N tasks from queue           Select N items from workflow queue
    │                                   │
    ▼                                   ▼
Dispatch all in parallel            Dispatch batch via polecat
    │                                   │
    ▼                                   ▼
Workers autonomous                  Workers autonomous
    │                                   │
    ▼                                   ▼
PR pipeline evaluates               Supervisor evaluates results
    │                                   │
    ▼                                   ▼
GitHub merges                       Accept / Revise / Escalate
    │                                   │
Done.                               Persist state → next burst
```

## When to Use Which

| Situation                                   | Mode           | Entry point                            |
| ------------------------------------------- | -------------- | -------------------------------------- |
| Queue of independent tasks, drain fast      | Swarm          | `polecat swarm` or `polecat supervise` |
| Decomposed epic, parallel subtasks          | Swarm          | `/swarm-supervisor` skill              |
| Process N items iteratively with evaluation | Burst          | `/burst-supervisor` skill              |
| Long-running workflow across sessions       | Burst          | `/burst-supervisor` + `/loop`          |
| One-off single task                         | Neither        | `polecat run -t <id>` or `/pull`       |
| Batch file processing (non-task)            | Atomic locking | See "Atomic Locking" appendix          |

**Rules of thumb:**

- If each task produces a PR and the PR pipeline can judge quality → swarm
- If you need to read and evaluate each result before dispatching more → burst
- If the work spans days or weeks → burst (state recovery across sessions)
- If you want maximum throughput right now → swarm

## Shared Infrastructure

Both modes build on the same polecat infrastructure. No mode has its own dispatch code — everything goes through `polecat run`.

### Worker Dispatch

All worker dispatch uses a single mechanism:

```bash
# Claude worker
polecat run -t <task-id> -p <project> -c <caller>

# Gemini worker
polecat run -t <task-id> -p <project> -c <caller> -g
```

This provides:

- **Worktree isolation**: Each worker gets `$POLECAT_HOME/polecat/<task-id>/`
- **Atomic claiming**: File-locking prevents duplicate claims
- **Agent invocation**: Claude or Gemini, with full task context
- **Auto-finish**: On exit 0, pushes branch and marks `merge_ready`
- **Transcript capture**: `$AOPS_SESSIONS/polecats/<task-id>.jsonl`

Workers never call `gemini -p` or `claude -p` directly.

### Task Queue

Both modes read from the same PKB task queue. Tasks are eligible for dispatch when:

- `status` is `active` or `ready`
- `assignee` is `polecat` or `bot`
- All `depends_on` are satisfied
- Task is a leaf (no children)

### Merge Pipeline

Worker output flows through the same merge pipeline regardless of mode:

1. Worker finishes → `polecat finish` → branch pushed, task `merge_ready`
2. PR created on GitHub (branch name: `polecat/<task-id>`)
3. PR review pipeline runs (custodiet, QA, Claude review)
4. GitHub auto-merge on approval
5. Task marked `done` on merge (GitHub Action)

### Worker Registry

Both modes read [[WORKERS.md]] for worker types, capabilities, selection rules, and capacity limits. Modify that file to change dispatch behavior without editing specs or skills.

## Swarm Mode

### Architecture

The swarm drains a task queue in parallel. Workers claim tasks independently — the supervisor's job is to select the batch and choose runners, then walk away.

```
┌──────────────┐     ┌──────────────────────────┐     ┌───────────┐
│  Task Queue  │────►│  Swarm (N workers)        │────►│  GitHub   │
│  (PKB)       │     │  Each: claim→work→PR      │     │  PRs      │
└──────────────┘     └──────────────────────────┘     └───────────┘
                                                            │
                                                            ▼
                                                      ┌───────────┐
                                                      │  Merge    │
                                                      │  Pipeline │
                                                      └───────────┘
```

### Entry Points

| Entry point                            | What it does                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------- |
| `polecat swarm -c N -g M -p <project>` | Spawn N Claude + M Gemini workers, each claims from queue                             |
| `polecat supervise -p <project> -n N`  | LLM supervisor selects (task, runner) pairs per round                                 |
| `/swarm-supervisor` skill              | Full 6-phase lifecycle: decompose → review → approve → dispatch → PR review → capture |

### Lifecycle (swarm-supervisor skill)

See [[skills/swarm-supervisor/SKILL.md]] for the full 6-phase protocol:

1. **Decompose**: Break large tasks into PR-sized subtasks
2. **Review**: Multi-agent review of decomposition
3. **Approve**: Human approval gate (surfaced via `/daily`)
4. **Dispatch**: Fire-and-forget via `polecat run` / `polecat swarm`
5. **PR Review**: GitHub Actions pipeline (automated)
6. **Capture**: Post-merge knowledge extraction

**Key property**: The supervisor does NOT actively monitor workers. After dispatch, the next touchpoint is when PRs arrive on GitHub.

### State (supervisor_loop.py)

The `polecat supervise` command uses `$POLECAT_HOME/supervisor-state-<project>.json` for round history. This is appropriate for swarm mode because:

- State is ephemeral (round history, not work-item tracking)
- The supervisor runs as a single process, not across sessions
- Workers report via exit codes and PR creation, not state updates

For long-running workflows that need per-item tracking, use burst mode instead.

### Conflict Avoidance

- **Atomic claiming**: `manager.py:claim_next_task()` with file locking
- **Worktree isolation**: Each worker in separate `$POLECAT_HOME/polecat/<task-id>/`
- **Batch isolation**: Mark non-batch tasks as `waiting` before dispatch to prevent claiming by `polecat swarm` (which claims ANY ready task)

## Burst Mode

### Architecture

The burst supervisor processes a workflow's queue iteratively across multiple invocations. Each burst: check results, evaluate, dispatch, persist, halt.

```
┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Tracking Task   │────►│  Burst N     │────►│  Workers     │
│  (state in PKB)  │     │  Evaluate    │     │  via polecat │
│                  │◄────│  Dispatch    │     │              │
│  Queue + Log     │     │  Persist     │     └──────────────┘
└──────────────────┘     └──────────────┘
        │
        ▼ (next invocation)
┌──────────────┐
│  Burst N+1   │
│  ...         │
└──────────────┘
```

### Entry Points

| Entry point                            | What it does                          |
| -------------------------------------- | ------------------------------------- |
| `/burst-supervisor init <description>` | Initialize new supervisor with queue  |
| `/burst-supervisor <tracking-task-id>` | Resume: evaluate + dispatch + persist |
| `/loop 30m /burst-supervisor <id>`     | Recurring bursts every 30 minutes     |

### State Schema

State lives in the tracking task body (PKB), not in external files. Designed in [[aops-f22cf622]].

**Important**: PKB strips unrecognized frontmatter fields. Supervisor state MUST live in a YAML code block in the task body, not in frontmatter.

**Body YAML code block** (structured, machine-readable):

- `queue[]` — per-item status, worker task reference, attempts
- `active_dispatches[]` — tasks currently being worked on
- `config` — burst size, max attempts, worker type, review mode
- `plan` — aggregate counters

**Body prose** (human-readable, append-only):

- Mission statement
- Workflow config (queue source, worker instructions, evaluation criteria)
- Progress log (one section per burst)
- Decision log
- Escalations

Any agent can resume by reading the tracking task. No filesystem state needed.

### Evaluation

The supervisor agent evaluates worker output using its own judgment — no code, no regex, no scoring functions. See [[skills/burst-supervisor/SKILL.md]] Phase 2a for the full evaluation protocol.

Three outcomes:

- **Accept**: Work meets criteria. Move on.
- **Revise**: Specific problems found. Create new worker task with feedback.
- **Fail**: Fundamental issues or retry budget exhausted. Escalate to human.

Evaluation criteria are written in plain language in the tracking task body, specific to the workflow.

### Concurrency

Single-agent-at-a-time (advisory). If `last_burst` < 5 minutes ago with active dispatches, warn and halt.

## Refinery (Merge Queue)

The Refinery processes `merge_ready` tasks regardless of which mode produced them.

### Implementation

`polecat/engineer.py` — the `Engineer` class:

1. **Scan**: Find oldest `merge_ready` task
2. **Claim merge slot**: Transition to `merging` (one at a time)
3. **Verify**: Fetch, check for unpushed commits
4. **Merge**: Squash merge to main
5. **Test**: Run `uv run pytest`
6. **Push**: Push to origin, delete branch
7. **Complete**: Task `done`, nuke worktree

### Failure Handling

On merge failure:

- Task status: `merging` → `review`
- Refinery Report appended to task body with timestamp and error
- Categorized: conflicts, tests_failed, dirty_worktree, other
- Returns to human intervention

### Merge Criteria

Auto-merge (no engineer review):

- Tests pass on branch
- No merge conflicts
- Low complexity (per [[WORKERS.md]] routing)

Engineer review triggered by:

- Higher complexity tasks
- Critical path tags (per [[WORKERS.md]])
- Random sampling
- Merge conflicts

## Configuration Separation

| Concern            | Spec (this document)     | WORKERS.md (soft config)               |
| ------------------ | ------------------------ | -------------------------------------- |
| Dispatch mechanism | `polecat run` always     | Runner selection rules                 |
| Worker types       | Architecture, lifecycle  | Names, capabilities, cost/speed        |
| Selection          | Decision tree structure  | Tag lists, complexity mappings         |
| Review routing     | Trigger logic            | Which complexity values trigger review |
| Monitoring         | Stall detection protocol | Heartbeat intervals, thresholds        |

To customize for a different deployment, modify WORKERS.md only.

## Status Lifecycle

```
active → in_progress → merge_ready → merging → done
                │              │           │
                │              │           └→ review (merge failed)
                │              └→ review (engineer review)
                └→ blocked (dependency, failure)
```

- `active` / `ready`: Eligible for claiming
- `in_progress`: Worker executing
- `merge_ready`: Worker finished, PR ready
- `merging`: Refinery processing (merge slot claimed)
- `review`: Engineer review or merge failure
- `waiting`: Human decision gate (swarm-supervisor Phase 3)
- `done`: Merged and complete
- `blocked`: Unresolved issue

## Appendix: Atomic Locking (Non-Task Batches)

For batch file processing that doesn't use the PKB task queue (e.g., processing 500 markdown files), the atomic locking pattern from the deprecated hypervisor remains useful:

```python
def claim_item(item_id: str) -> bool:
    lock_dir = Path(f"/tmp/batch/locks/{item_id}")
    try:
        lock_dir.mkdir(exist_ok=False)  # Atomic on POSIX
        return True
    except FileExistsError:
        return False
```

Use this only for non-task operations where PKB task tracking is overkill. For anything that should be tracked as a task, use the PKB queue with polecat's atomic claiming.

## Appendix: Migration from Deprecated Patterns

### supervisor_loop.py State

`supervisor_loop.py` currently persists round history to `$POLECAT_HOME/supervisor-state-<project>.json`. This remains appropriate for swarm mode (ephemeral rounds). For long-running workflows requiring per-item tracking, use burst mode with task-body state instead.

No migration needed — the two state patterns serve different use cases.

### Hypervisor Skill

The `/hypervisor` skill is deprecated for task orchestration. `polecat swarm` provides worktree isolation, API-based claiming, and auto-restart — all improvements over the shared-worktree model.

The atomic locking pattern (above) is the only surviving element, retained for non-task batch operations.

### Worker-Hypervisor Spec

`specs/worker-hypervisor.md` is superseded by this document. Its empirical findings (2026-01-22) confirmed that parallel spawning works but shared worktrees cause conflicts — exactly the problem polecat worktrees solved.

## Related

- [[specs/polecat-system.md]] — Foundation: worktrees, bare mirrors, task claiming
- [[skills/swarm-supervisor/SKILL.md]] — Swarm mode skill (6-phase lifecycle)
- [[skills/burst-supervisor/SKILL.md]] — Burst mode skill (iterative dispatch + evaluation)
- [[WORKERS.md]] — Worker registry (soft config)
- [[LIFECYCLE-HOOKS.md]] — Trigger hooks
