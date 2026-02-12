---
title: Polecat Swarms & Engineer Review
type: spec
description: Specification for parallel polecat swarms, automated merging, and engineer agent review workflow
status: DRAFT
---

# Polecat Swarms & Engineer Review

## Giving Effect

- [[polecat/swarm.py]] - Swarm orchestration: parallel worker management
- [[polecat/engineer.py]] - Refinery and Engineer agent for merge queue processing
- [[polecat/manager.py]] - Worktree management (`claim_next_task` with atomic locking)
- [[skills/hypervisor/SKILL.md]] - Hypervisor skill for batch parallel processing
- [[skills/swarm-supervisor/SKILL.md]] - Swarm supervisor skill (dispatch protocol)
- [[WORKERS.md]] - Worker registry (types, capabilities, selection rules, thresholds)
- [[specs/polecat-system.md]] - Foundation system this builds upon

**Goal**: Scale development throughput by enabling multiple concurrent "polecat" workers to execute tasks in parallel, while maintaining high code quality through an automated "Refinery" and an intelligent "Engineer" review gate.

## 1. Swarm Architecture

The Swarm builds upon the [Polecat System](./polecat-system.md) (ephemeral git worktrees) to allow multiple agents to work simultaneously on the same repository without file locking or branch conflicts.

### Components

- **Task Queue**: The single source of truth (TaskDB). Holds tasks in `ready` state.
- **Worker Registry**: [[WORKERS.md]] defines available worker types, capabilities, selection rules, and operational thresholds. Deployment-specific; modify without changing code or skill prompts.
- **Swarm Workers**: Independent agent instances, each operating in its own isolated polecat worktree (`~/.aops/polecat/<task-id>`). Worker types and dispatch rules are configured in the registry.
- **The Refinery**: A centralized process (or singleton agent) responsible for integrating completed work.
- **Engineer Agent**: A specialized persona responsible for code review and quality assurance.

### Workflow

```mermaid
flowchart LR
    Queue[Task Queue] -->|Claim| Worker1[Polecat Worker 1]
    Queue -->|Claim| Worker2[Polecat Worker 2]
    Queue -->|Claim| Worker3[Polecat Worker 3]

    Worker1 -->|Finish| MergeReady[Status: merge_ready]
    Worker2 -->|Finish| MergeReady
    Worker3 -->|Finish| MergeReady

    MergeReady -->|Queue| Refinery

    Refinery -->|Simple/Safe| AutoMerge[Auto Merge]
    Refinery -->|Complex/Risk| Engineer[Engineer Review]

    Engineer -->|Approve| AutoMerge
    Engineer -->|Reject| Return[Return to Worker]

    AutoMerge -->|Success| Done[Status: done]
    AutoMerge -->|Fail| Return
```

### Conflict Avoidance

- **Atomic Claiming**: `TaskStorage` provides atomic `update_task` operations. Workers "claim" a task by setting status to `in_progress`.
- **Isolation**: Each worker has a dedicated git worktree/branch.
- **Rebasing**: Workers must rebase on `main` before `polecat finish` to ensure their branch is current, reducing merge conflicts in the Refinery.

## 2. Auto-merge System (The Refinery)

The Refinery is the "merge queue" processor. It serializes the integration of parallel work to maintain a green build.

### Criteria for Auto-merge

A task qualifies for immediate auto-merge _without_ human/engineer intervention if:

1. **Tests Pass**: CI checks (pre-commit, unit tests) pass on the branch.
2. **No Conflicts**: Merge to `main` is clean.
3. **Low Complexity**: Task complexity is `mechanical` or equivalent (see Complexity Routing in [[WORKERS.md]] for current values).
4. **Verified Author**: The change was produced by a trusted tool/workflow (e.g., automated refactor).

### Merge Strategy

1. **Lock**: Pick oldest `merge_ready` task.
2. **Verify**: Run project validation (lint/test) one last time on the merge commit candidate.
3. **Merge**: Squash merge to `main`.
4. **Push**: Push to origin.
5. **Cleanup**: Delete branch and worktree.

## 3. Engineer Agent Review

The "Engineer" is a specialized agent invocation that acts as a quality gate. It is triggered by the Refinery when a task does not meet auto-merge criteria or requires judgment.

### Triggers

- **Complexity**: Task complexity routes to Engineer review (see Complexity Routing in [[WORKERS.md]] for which values trigger review vs auto-merge).
- **Heuristics**: Changes touch critical paths (tags matching high-stakes tags in [[WORKERS.md]]).
- **Random Sampling**: % of `mechanical` tasks are reviewed to prevent drift.
- **Merge Conflict**: Refinery fails to auto-merge; Engineer attempts to resolve or kicks back.

### Review Workflow

1. **Checkout**: Engineer spins up a viewing context (or reuses the polecat).
2. **Analysis**:
   - **Code Quality**: Linter checks, complexity analysis.
   - **Test Coverage**: Did the worker add tests? Do they pass?
   - **Architectural Fit**: Does the change align with `AXIOMS.md` and `HEURISTICS.md`?
3. **Decision**:
   - **Approve**: Signs off. Refinery proceeds to merge.
   - **Request Changes**: Annotates task with specific feedback. Status -> `in_progress` (or assigned back to worker).
   - **Reject**: Marks task as `cancelled` or `blocked` if fundamentally flawed.

## 4. Design Resolutions

### How do swarm workers claim tasks without conflicts?

Utilize the existing `TaskStorage` backend. Workers query for `status=active` and perform an atomic CAS (Compare-And-Swap) or locked update to `status=in_progress` + `assignee=<worker-id>`.

### Rollback Strategy

If a merged task causes regression (detected post-merge):

1. **Detect**: Monitoring/User report -> New `bug` task created.
2. **Revert**: Refinery/Engineer executes `git revert <commit-hash>`.
3. **Reopen**: The original task is set back to `in_progress` (or `todo`) with the bug report appended to its body.

### Status Workflow Integration

Existing: `active` -> `in_progress` -> `merge_ready` -> `done`

**Revised with Swarm/Engineer**:

- `active`: Ready for worker.
- `in_progress`: Worker executing.
- `merge_ready`: Worker finished. Waiting for Refinery.
- `review`: (New/Refined) Refinery routed to Engineer for review.
- `approved`: (New internal state) Engineer approved, waiting for merge.
- `done`: Merged.
- `blocked`: Kickback/Conflict requiring human intervention.

## 5. Configuration Separation

This spec describes the **architecture and protocols** (hard). Deployment-specific
parameters are in **[[WORKERS.md]]** (soft):

| Concern | Spec (hard) | WORKERS.md (soft) |
|---------|------------|-------------------|
| Worker types | Architecture, lifecycle | Names, capabilities, cost/speed |
| Selection | Decision tree structure | Tag lists, complexity mappings, thresholds |
| Monitoring | Stall detection protocol | Heartbeat intervals, alert thresholds |
| Failure handling | Recovery protocol structure | Exit codes, retry limits, backoff |
| Review routing | Engineer trigger logic | Which complexity values trigger review |
| Domain review | Specialist invocation protocol | Specialist registry, domain mappings |

To customize for a different deployment, modify WORKERS.md only.

## 6. Future Work

- **Speculative Merging**: Run tests on "virtual" merges of queued tasks to predict conflicts early.
- **Reviewer Personas**: Different "Engineer" profiles (Security, Perf, Style).
