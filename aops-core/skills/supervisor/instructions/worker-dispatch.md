# Worker Dispatch

Supervisor dispatches individual tasks to workers. This phase transforms
approved decomposition into execution — one task at a time.

---

## Worker Types and Capabilities

> **Configuration**: See [[WORKERS.md]] for current worker types, capabilities,
> cost/speed profiles, and capacity limits. Modify that file to add workers or
> change profiles without editing this skill.

Load worker registry before dispatch. Each worker has:

- **Capabilities**: What task types it can handle
- **Cost/Speed**: Resource trade-offs (1-5 scale)
- **Max Concurrent**: Capacity limit for parallel dispatch
- **Best For**: Recommended use cases

---

## Pre-Dispatch Validation (MANDATORY)

Before dispatching ANY task to a worker, the supervisor must validate:

1. **Target currency**: Are the files/modules the task will touch still current? Check for:
   - Deprecated code (superseded by another implementation, possibly in a different repo)
   - Files that no longer exist on the default branch
   - Components that have been rewritten or moved

2. **Repo correctness**: Does the task belong in this repository? Check the task body and AC for references to other repos. If the task's deliverable lives elsewhere, redirect it — don't dispatch.

3. **AC implementability**: Can the acceptance criteria be met with the current codebase? If AC references APIs, tools, or patterns that no longer exist, the task needs updating before dispatch.

**If validation fails**: Update the task with findings, set status to `blocked`, and skip it. Do NOT dispatch tasks that will produce wasted work.

**Why this matters**: Without runtime hydration (gate is off), this pre-dispatch check is the last opportunity to catch tasks aimed at deprecated code. The 2026-03-22 dogfood run lost a full worker cycle to a task targeting superseded Python files (GH #224).

## Worker Selection

**Step 1: Assess Task Requirements**

Extract required capabilities from task metadata:

```markdown
## Task Analysis for Worker Selection

**Task**: <task-id>
**Tags**: [list from task.tags]
**Complexity**: <task.complexity or inferred>
**Files affected**: <count from decomposition>
**Estimated effort**: <from decomposition>

### Required Capabilities

[Map task characteristics to capabilities]

### Constraints

- Deadline pressure: [yes/no]
- Budget sensitivity: [yes/no]
- Quality criticality: [low/medium/high]
```

**Step 2: Apply Selection Rules**

> **Configuration**: Selection rules (tag routing, complexity routing, heuristic
> thresholds) are defined in [[WORKERS.md]]. Modify that file to change routing
> behavior.

Apply rules in priority order:

1. **Complexity routing**: Match task.complexity against Complexity Routing table
2. **Tag routing**: Check task.tags against High-Stakes and Bulk tag lists
3. **Heuristic thresholds**: Apply file count and effort rules
4. **Default**: Use configured default worker (typically claude for safety)

**Step 3: Check Capacity**

Before dispatch, verify worker availability against limits in [[WORKERS.md]].

1. Load Max Concurrent for selected worker type from WORKERS.md
2. Count in_progress tasks assigned to that worker type
3. If at capacity:
   - Try fallback worker if task capabilities permit
   - Otherwise queue task for later dispatch

---

## Dispatch Protocol

**Single Task Dispatch**:

```bash
# Claude worker for a specific task (by task ID)
polecat run -t <task-id> -p <project>

# Gemini worker for a specific task
polecat run -t <task-id> -p <project> --gemini

# Claude worker claiming next ready task from queue
polecat run -p <project>

# Gemini worker claiming next ready task from queue
polecat run -g -p <project>

# Jules (asynchronous, runs on Google infrastructure)
aops task <task-id> | jules new --repo <owner>/<repo>
```

**Jules Dispatch Notes**:

- Pipe task context from `aops task` into `jules new` — this gives Jules the full task body, relationships, and acceptance criteria
- Jules sessions are asynchronous — returns a session URL immediately
- Check status: `jules remote list --session`
- One session per task
- Sessions show "Completed" when coding is done but require human approval on Jules web UI before branches are pushed and PRs are created

**Dispatch Recording** (in epic task body, BEFORE firing the worker):

Update the work items table with status `dispatched`, the worker type, and
the dispatch timestamp. The supervisor checks status on next orient phase.

```markdown
### Dispatch Log

[ISO timestamp] [environment]: Dispatched task-abc to claude via polecat run
```

---

## Post-Dispatch

After dispatch, update the work items table in the epic task body. The
supervisor checks status on its next invocation (orient phase) — it does
not actively poll.

**Stale task cleanup** (periodic, not real-time):

```bash
# Reset tasks stuck in_progress for >4 hours (cron or manual)
polecat reset-stalled --hours 4 --dry-run
polecat reset-stalled --hours 4
```

This is a janitorial operation. Run it periodically (e.g., via `stale-check`
cron hook) to clean up crashed workers.

**Worker failures surface as missing PRs.** If a worker fails, no PR appears.
The task stays `in_progress` until the stale-check resets it to `active` for
the next dispatch cycle.

**Known issue: auto-finish override loop.** When a task was already completed
by another worker (e.g., Jules fixed it), polecat auto-finish detects zero
changes and resets to active, creating an infinite retry loop. Workaround:
mark the task `done` manually. See `aops-fdc9d0e2`.

---

## Parallel Execution Coordination

Workers coordinate through the task system, not through the supervisor:

**Dependency Respect**:

- Workers only claim tasks with satisfied `depends_on`
- Polecat CLI `claim_next_task()` in `manager.py` enforces this via atomic file locking
- No supervisor verification needed at runtime

**Conflict Prevention**:

- Each polecat worker operates in isolated worktree
- No two workers touch same task (atomic claiming)
- Jules sessions are isolated by design (separate Google infrastructure)
- If decomposition reveals shared files:
  - Add explicit `depends_on` between subtasks before dispatch
