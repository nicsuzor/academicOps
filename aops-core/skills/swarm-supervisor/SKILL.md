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

Orchestrate the complete non-interactive agent workflow: decompose → review → approve → execute → merge → capture.

## Design Philosophy

**Agents decide, code triggers.** This skill provides prompt instructions for agent-driven orchestration. The supervisor agent makes all substantive decisions (decomposition strategy, reviewer selection, worker dispatch). Code is limited to:

- **Hooks**: Triggers that start agent work (shell scripts, cron)
- **MCP tools**: Task state management (create, update, complete)
- **CLI**: Worker spawning via `polecat run` or `polecat swarm` (see Command Selection below)

## Lifecycle Phases

```
┌─────────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐    ┌───────┐    ┌─────────┐
│  DECOMPOSE  │───►│  REVIEW  │───►│ APPROVE │───►│ EXECUTE  │───►│ MERGE │───►│ CAPTURE │
│  (agent)    │    │ (agents) │    │ (human) │    │ (workers)│    │(human)│    │ (agent) │
└─────────────┘    └──────────┘    └─────────┘    └──────────┘    └───────┘    └─────────┘
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

### Phase 4: Worker Execution

Supervisor dispatches workers based on task requirements. This phase transforms approved decomposition into parallel execution.

> See [[instructions/worker-execution]] for worker types, selection protocols, dispatching, and failure handling.

### Phase 5: PR Review & Merge

Human gate. Supervisor surfaces merge-ready tasks in daily note.

```markdown
## Ready to Merge

| PR          | Task         | Tests | Reviews     | Summary           |
| ----------- | ------------ | ----- | ----------- | ----------------- |
| [#123](url) | [[task-abc]] | Pass  | 3/3 APPROVE | Added auth module |
```

**Merge via**:

- `gh pr merge --squash --delete-branch`
- Or GitHub Actions auto-merge for clean PRs

### Phase 6: Knowledge Capture

Post-merge, supervisor extracts learnings.

> See [[instructions/knowledge-capture]] for the knowledge extraction protocol.

---

## Lifecycle Trigger Hooks

External triggers that start lifecycle phases. Shell scripts check
preconditions (is queue non-empty?) and start supervisor sessions.
All dispatch decisions are made by this supervisor agent, not by scripts.

> **Configuration**: See [[LIFECYCLE-HOOKS.md]] for notification settings
> and cron schedules. See [[WORKERS.md]] for runner types, capabilities,
> and sizing defaults — the supervisor reads these at dispatch time.

| Hook          | Trigger        | What it does                            | Script                                   |
| ------------- | -------------- | --------------------------------------- | ---------------------------------------- |
| `queue-drain` | cron / manual  | Checks queue, starts supervisor session | `scripts/hooks/lifecycle/queue-drain.sh` |
| `post-finish` | polecat finish | Sends completion notification           | `scripts/hooks/lifecycle/post-finish.sh` |
| `stale-check` | cron / manual  | Resets tasks stuck beyond threshold     | `scripts/hooks/lifecycle/stale-check.sh` |
| `merge-ready` | cron / manual  | Lists merge-ready PRs, notifies         | `scripts/hooks/lifecycle/merge-ready.sh` |

**Agent-driven dispatch**: When `queue-drain.sh` starts a supervisor session,
the supervisor (this skill) reads WORKERS.md, inspects the task queue via
MCP, and decides which runners to invoke and how many. Any runner that
claims tasks via `claim_next_task()` and reports completion status works.

---

# Parallel Worker Orchestration

Orchestrate multiple parallel polecat workers, each with isolated git worktrees. This replaces the deprecated hypervisor patterns.

> See [[references/parallel-worker-orchestration]] for architecture, usage, and troubleshooting.

## Polecat Command Selection

Choose the right subcommand based on dispatch intent:

| Intent | Command | When to use |
|--------|---------|-------------|
| Run a specific task by ID | `polecat run -t <task-id>` | "Commission a polecat for THIS task" |
| Claim next ready task from a project | `polecat run -p <project>` | "Run the next thing in aops" |
| Batch drain queue with parallel workers | `polecat swarm -c N -p <project>` | "Drain the queue", multiple tasks |

`run` executes a single claim-setup-work-finish cycle. `swarm` spawns N parallel workers that each run cycles continuously until the queue is empty. **Never use `swarm` to target a single known task** — use `run -t`.

## Related

- `/pull` - Single task workflow (what each worker runs internally)
- `polecat run` - Single autonomous polecat (no swarm)
- `polecat crew` - Interactive, persistent workers
- `hypervisor` - Deprecated; atomic lock pattern still useful for non-task batches
- `/q` - Quick-queue tasks for swarm to implement
- `LIFECYCLE-HOOKS.md` - Configurable trigger parameters (thresholds, notifications, runner)
- `WORKERS.md` - Worker types, capabilities, sizing defaults
