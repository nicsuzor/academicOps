---
name: swarm-supervisor
description: Orchestrate parallel polecat workers with isolated worktrees. Use polecat swarm for production parallel task processing.
triggers:
  - "polecat swarm"
  - "polecat herd"
  - "spawn polecats"
  - "run polecats"
  - "parallel workers"
  - "batch tasks"
  - "parallel processing"
  - "supervise tasks"
  - "orchestrate workflow"
---

# Swarm Supervisor - Full Lifecycle Orchestration

Orchestrate the complete non-interactive agent workflow: decompose → review → approve → dispatch → PR review → capture.

## Design Philosophy

**Dispatch and walk away.** The supervisor's job ends at dispatch. Once tasks
are sent to workers (polecat, Jules, or any other), the next touchpoint is
when pull requests arrive on GitHub. Workers are autonomous — they claim tasks,
do the work, push branches, and create PRs. Everything between dispatch and
PR is the worker's problem.

- **Supervisor decides**: Task curation, worker selection, batch composition
- **Workers execute**: Autonomously, with no supervisor monitoring
- **GitHub handles**: PR review pipeline, merge gates, CI checks
- **GitHub Actions closes the loop**: PR merge → task marked done

Code is limited to:

- **MCP tools**: Task state management (create, update, complete)
- **CLI**: Worker spawning via `polecat swarm` or `jules new`
- **GitHub Actions**: Automated PR review and task completion on merge

## Lifecycle Phases

```
┌─────────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐    ┌───────────┐    ┌─────────┐
│  DECOMPOSE  │───►│  REVIEW  │───►│ APPROVE │───►│ DISPATCH │───►│ PR REVIEW │───►│ CAPTURE │
│  (agent)    │    │ (agents) │    │ (human) │    │(sup+fire)│    │(GH Action)│    │ (agent) │
└─────────────┘    └──────────┘    └─────────┘    └──────────┘    └───────────┘    └─────────┘
```

### Phase 1: Decompose & Phase 2: Multi-Agent Review

The supervisor decomposes large tasks into PR-sized subtasks and invokes reviewer agents to synthesize their feedback.

> See [[instructions/decomposition-and-review]] for detailed protocols on decomposition and multi-agent review.

### Phase 3: Human Approval Gate

Task waits for human decision. Surfaced via `/daily` skill in daily note.

**User Actions**:

| Action          | Task State    | Notes                           |
| --------------- | ------------- | ------------------------------- |
| Approve         | → in_progress | Subtasks created, first claimed |
| Request Changes | → decomposing | Feedback attached               |
| Send Back       | → pending     | Assignee cleared                |
| Backburner      | → dormant     | Preserved but inactive          |
| Cancel          | → cancelled   | Reason required                 |

### Phase 4: Dispatch (fire and forget)

Supervisor selects workers, dispatches tasks, and **walks away**. No active
monitoring — the supervisor's job ends here.

> See [[instructions/worker-execution]] for worker types, selection protocols,
> and dispatch commands.

**Dispatch flow:**

1. Curate batch: select tasks, set complexity, confirm assignees
2. Mark non-approved tasks as `waiting` to prevent accidental claiming
3. Dispatch: `polecat swarm` for polecat workers, `jules new` for Jules
4. Done. Next touchpoint is when PRs arrive.

**Known limitations (from dogfooding sessions):**

- `polecat swarm` claims ANY ready task in the project, not just the curated
  batch. Mark non-batch tasks as `waiting` to prevent claiming. See `aops-2e13ecb4`.
- Auto-finish overrides manual task completion when a task was already fixed
  by another worker. See `aops-fdc9d0e2`.

### Phase 5: PR Review & Merge

**GitHub-native.** PRs arrive from workers (polecat branches, Jules PRs).
The `pr-review-pipeline.yml` GitHub Action handles automated review. Human
merges via GitHub UI or auto-merge for clean PRs.

The supervisor does NOT actively monitor for merge-ready PRs. PRs surface
naturally through GitHub's notification system and the PR review pipeline.

**Task completion on merge**: When a PR merges, a GitHub Action parses the
task ID from the branch name (`polecat/aops-XXXX`) and marks the task done.
This closes the loop without supervisor involvement.

**Merge via**:

- GitHub UI: review, approve, merge
- `gh pr merge --squash --delete-branch` from CLI
- Auto-merge via GitHub Actions for PRs that pass all checks

### Phase 6: Knowledge Capture

Post-merge, supervisor extracts learnings.

> See [[instructions/knowledge-capture]] for the knowledge extraction protocol.

---

## Lifecycle Trigger Hooks

External triggers that start lifecycle phases. The supervisor is invoked
for dispatch decisions; everything after dispatch is handled by workers
and GitHub Actions.

> **Configuration**: See [[WORKERS.md]] for runner types, capabilities,
> and sizing defaults — the supervisor reads these at dispatch time.

| Hook           | Trigger          | What it does                            |
| -------------- | ---------------- | --------------------------------------- |
| `queue-drain`  | cron / manual    | Checks queue, starts supervisor session |
| `stale-check`  | cron / manual    | Resets tasks stuck beyond threshold     |
| `pr-merge`     | GitHub Action    | PR merged → mark task done              |

**Agent-driven dispatch**: The supervisor reads WORKERS.md, inspects the
task queue via MCP, and decides which runners to invoke and how many.
Any runner that creates PRs from task work is compatible.

---

# Parallel Worker Orchestration

Orchestrate multiple parallel polecat workers, each with isolated git worktrees. This replaces the deprecated hypervisor patterns.

> See [[references/parallel-worker-orchestration]] for architecture, usage, and troubleshooting.

## Related

- `/pull` - Single task workflow (what each worker runs internally)
- `polecat run` - Single autonomous polecat (no swarm)
- `polecat crew` - Interactive, persistent workers
- `hypervisor` - Deprecated; atomic lock pattern still useful for non-task batches
- `/q` - Quick-queue tasks for swarm to implement
- `LIFECYCLE-HOOKS.md` - Configurable trigger parameters (thresholds, notifications, runner)
- `WORKERS.md` - Worker types, capabilities, sizing defaults
