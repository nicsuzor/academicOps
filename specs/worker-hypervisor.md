---
title: Worker-Hypervisor Architecture
type: spec
description: Architecture for parallel task execution with worker agents pulling from bd and a hypervisor managing concurrency
status: DRAFT
---

# Worker-Hypervisor Architecture

## Giving Effect

- [[skills/hypervisor/SKILL.md]] - Hypervisor skill for batch parallel processing with atomic locking
- [[polecat/swarm.py]] - Swarm orchestration for parallel workers
- [[polecat/manager.py]] - Atomic task claiming via Polecat CLI to prevent race conditions
- [[commands/pull.md]] - `/pull` command that workers execute
- [[specs/polecat-swarms.md]] - Swarm architecture built on polecat worktrees

**Goal**: Enable parallel task execution where multiple worker agents independently pull and complete tasks from bd, coordinated by a hypervisor that maintains a pool of active workers.

## Problem Statement

Current execution is single-threaded: one agent handles one task at a time. For batch operations or complex projects with many independent subtasks, this is inefficient. We need:

1. **Worker agents** that can autonomously pull, execute, and complete bd tasks
2. **A hypervisor** that manages a pool of workers (4-8 concurrent)
3. **Clear boundaries** so workers don't conflict with each other

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        HYPERVISOR                               │
│                                                                 │
│   Responsibilities:                                             │
│   - Maintain pool of 4-8 active workers                         │
│   - Monitor worker health and completion                        │
│   - Spawn new workers as others complete                        │
│   - Aggregate results and report progress                       │
│   - Handle worker failures (retry, escalate)                    │
│                                                                 │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│   │Worker 1 │ │Worker 2 │ │Worker 3 │ │Worker 4 │  ...         │
│   │  (bd    │ │  (bd    │ │  (bd    │ │  (bd    │              │
│   │  task)  │ │  task)  │ │  task)  │ │  task)  │              │
│   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘              │
│        │           │           │           │                    │
│        ▼           ▼           ▼           ▼                    │
│   ┌─────────────────────────────────────────────────┐          │
│   │                bd (beads)                        │          │
│   │    Task queue with status tracking               │          │
│   └─────────────────────────────────────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Worker Agent

### Worker Purpose

A worker agent is a self-contained execution unit that:

1. Pulls a single task from bd
2. Receives full context needed to execute
3. Executes the task following framework workflows
4. Reports completion/failure back

### Worker Agent Definition

```yaml
name: worker
description: Autonomous task executor that pulls and completes bd issues
type: agent
model: sonnet
tools: [Read, Write, Edit, Bash, Glob, Grep, TodoWrite, Task]
```

### Worker Context Injection

When a worker is spawned, it receives a **hydrated context chunk** containing:

```markdown
## Worker Task Context

**BD Issue**: <id>
**Title**: <issue title>
**Description**: <full issue description>
**Priority**: <priority>
**Type**: <task|bug|feature|chore>
**Dependencies**: <list of blocking issues, if any>

### Issue Details

<full bd show output>

### Relevant Files

<files mentioned in issue or identified by hypervisor>

### Constraints

- Working directory: <specific directory if scoped>
- Scope: <what worker CAN modify>
- Out of scope: <what worker MUST NOT touch>

### Success Criteria

1. <specific criterion from issue>
2. <another criterion>
3. Tests pass
4. bd issue closed

### Workflow

Follow [[<workflow-id>]] workflow for this task type.
```

### Worker Execution Flow

```
Worker spawned with task context
    │
    ├─ 1. Validate context is complete
    │      - If missing info: FAIL FAST, report to hypervisor
    │
    ├─ 2. Claim task in bd
    │      bd update <id> --status=in_progress
    │
    ├─ 3. Execute workflow
    │      - Follow assigned workflow
    │      - Use TodoWrite for progress tracking
    │      - Respect scope boundaries
    │
    ├─ 4. Run quality gates
    │      - Tests pass
    │      - QA verification (if applicable)
    │
    ├─ 5. Commit and close
    │      git add -A && git commit -m "..."
    │      bd close <id>
    │
    └─ 6. Report completion to hypervisor
           - Success: task id, commit hash
           - Failure: task id, error, partial progress
```

### Worker Boundaries

Workers MUST:

- Stay within their assigned scope
- Not modify files outside their task scope
- Report immediately if they encounter out-of-scope issues
- Fail fast on ambiguity or missing context

Workers MUST NOT:

- Claim additional tasks (one task per worker)
- Push to remote (hypervisor coordinates pushes)
- Modify shared state without coordination
- Continue if tests fail

## Hypervisor Agent

### Hypervisor Purpose

The hypervisor is a coordination layer that:

1. Maintains a pool of active workers
2. Assigns tasks to workers with proper context
3. Monitors worker health and progress
4. Aggregates results and handles failures
5. Coordinates git operations (single push point)

### Hypervisor Agent Definition

```yaml
name: hypervisor
description: Coordinates parallel worker execution for batch task processing
type: agent
model: opus
tools: [Read, Bash, Task, TodoWrite]
```

### Hypervisor Execution Flow

```
Hypervisor starts
    │
    ├─ 1. Assess work queue
    │      bd ready
    │      bd list --status=open
    │      Identify independent tasks (no blockers)
    │
    ├─ 2. Hydrate task contexts
    │      For each task:
    │      - Generate worker context chunk
    │      - Identify relevant files
    │      - Set scope boundaries
    │
    ├─ 3. Spawn worker pool
    │      - Spawn 4-8 workers with Task()
    │      - Each worker gets one task context
    │      - Track worker → task mapping
    │
    ├─ 4. Monitor and refill
    │      Loop:
    │      - Check worker completion
    │      - On success: record result, spawn new worker if tasks remain
    │      - On failure: retry once, then log and continue
    │      - Continue until no tasks remain
    │
    ├─ 5. Aggregate and push
    │      - Collect all commits
    │      - Run combined test suite
    │      - git pull --rebase && git push
    │      - bd sync
    │
    └─ 6. Report summary
           - Tasks completed
           - Tasks failed (with reasons)
           - Follow-up issues created
```

### Concurrency Management

**Task Independence**: Only assign tasks to workers if:

- Task has no blockers (or blockers are completed)
- Task doesn't modify same files as another active worker
- Task scope doesn't overlap with active workers

**Git Coordination**: Workers commit locally, hypervisor pushes:

- Workers: `git add -A && git commit -m "..."`
- Hypervisor: After all workers complete, `git pull --rebase && git push`
- This prevents push conflicts and ensures atomic batch operations

**Failure Handling**:

```
Worker reports failure
    │
    ├─ Is it retryable? (transient error, timeout)
    │      Yes → Spawn new worker with same task
    │      No  → Log failure, continue with other tasks
    │
    ├─ Did worker partially complete?
    │      Yes → Save progress, create follow-up issue
    │      No  → Mark task as blocked, note error
    │
    └─ Is pool depleted?
           Yes → Report partial completion
           No  → Continue with remaining workers
```

## Success Criteria

1. Workers can independently complete tasks without supervision
2. Hypervisor maintains 4-8 concurrent workers
3. Git operations don't conflict (single push point)
4. Failures are handled gracefully (retry, log, continue)
5. Combined test suite passes before push
6. bd state accurately reflects work state

## Empirical Findings (2026-01-22)

Tested parallel worker spawning with 5 haiku workers on aops framework tasks:

### Results

| Metric                | Result     |
| --------------------- | ---------- |
| Spawn success         | 5/5 (100%) |
| Execution success     | 5/5 (100%) |
| Conflicts/collisions  | 0          |
| Commits produced      | 5          |
| Notification delivery | 4/5 (80%)  |

### Confirmed Working

- Raw `Task()` parallel spawning works without conflicts
- Workers execute independently and produce commits
- No resource contention observed
- Task status updates are reliable (can verify via MCP)

### Issues Identified

1. **Notification reliability**: 20% of task-notification messages never arrived
2. **Notification latency**: Delivered notifications were 2-5 minutes delayed
3. **Output file cleanup**: `/tmp/claude/.../tasks/*.output` files deleted after completion
4. **No real-time visibility**: Must poll git log or task status to verify completions

### Recommendations

1. Investigate notification delivery pipeline for reliability
2. Add worker summary persistence (to task body or memory)
3. Consider batch status aggregator for parallel operations
4. Retain output files for configurable duration post-completion

## Future Enhancements

1. **Worker specialization**: Different worker types for different task categories
2. **Dynamic pool sizing**: Adjust worker count based on task complexity
3. **Priority-aware scheduling**: High-priority tasks get workers first
4. **Cross-repository coordination**: Workers spanning multiple repos
5. **Persistent hypervisor**: Long-running hypervisor that monitors bd continuously
6. **Notification reliability**: Fix missing/delayed completion notifications
7. **Batch status dashboard**: Real-time view of parallel worker progress

## Implementation Phases

### Phase 1: Worker Agent (Current Task)

- Create worker agent definition in `agents/worker.md`
- Worker receives context, executes, reports
- Single-worker testing

### Phase 2: Hypervisor Agent

- Create hypervisor agent definition in `agents/hypervisor.md`
- Task assignment and context generation
- Multi-worker orchestration

### Phase 3: Integration

- Wire hypervisor to batch-processing workflow
- Add to prompt-hydrator routing
- End-to-end testing with real bd tasks
