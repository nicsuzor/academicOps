# Swarm Supervisor: Worker Execution

## Phase 4: Worker Execution

Supervisor dispatches workers based on task requirements. This phase transforms approved decomposition into parallel execution.

---

### 4.1 Worker Types and Capabilities

> **Configuration**: See [[WORKERS.md]] for current worker types, capabilities,
> cost/speed profiles, and capacity limits. Modify that file to add workers or
> change profiles without editing this skill.

Load worker registry before dispatch. Each worker has:

- **Capabilities**: What task types it can handle
- **Cost/Speed**: Resource trade-offs (1-5 scale)
- **Max Concurrent**: Capacity limit for parallel dispatch
- **Best For**: Recommended use cases

---

### 4.2 Worker Selection Protocol

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

```markdown
## Worker Selection Decision Tree

1. **Complexity routing**: Match task.complexity against Complexity Routing table
2. **Tag routing**: Check task.tags against High-Stakes and Bulk tag lists
3. **Heuristic thresholds**: Apply file count and effort rules
4. **Default**: Use configured default worker (typically claude for safety)
```

The supervisor loads current rules from WORKERS.md and applies them to each task.

**Step 3: Check Capacity**

Before dispatch, verify worker availability against limits in [[WORKERS.md]].

```markdown
## Capacity Check

1. Load Max Concurrent for selected worker type from WORKERS.md
2. Count in_progress tasks assigned to that worker type
3. If at capacity:
   - Try fallback worker if task capabilities permit
   - Otherwise queue task for later dispatch
```

Capacity overflow actions are worker-specific (some allow substitution, others queue only).

---

### 4.3 Dispatch Protocol

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
jules new --repo <owner>/<repo> "<task description>"
```

**Jules Dispatch Notes**:

- Jules takes a plain-text prompt via pipe: `echo "<prompt>" | jules new --repo <owner>/<repo>`
- Multiline prompts in quotes hang the CLI; always pipe instead
- Jules sessions are asynchronous — returns a session URL immediately
- Check status: `jules remote list --session`
- One session per task; use `--parallel N` only for independent subtasks
- Include task ID in prompt text so PRs can be linked back to tasks

**Batch Dispatch (Swarm)**:

When multiple approved subtasks are ready:

```bash
# Calculate swarm composition
# Based on: ready_tasks, task_mix, budget, deadline

# Example: 5 ready tasks, 3 code-heavy, 2 doc-heavy
polecat swarm -c 2 -g 2 -p <project>
```

**Swarm Sizing Heuristics**:

> **Configuration**: See Swarm Sizing Defaults in [[WORKERS.md]] for recommended
> compositions based on queue size and task mix.

Calculate swarm composition from:

- Number of ready tasks
- Task complexity/type distribution
- Current capacity limits
- Budget constraints (if applicable)

**Dispatch Output Format** (appended to parent task body):

```markdown
## Worker Dispatch Log

**Dispatched**: <timestamp>
**Swarm**: <worker counts by type>

### Task Assignments

| Task         | Worker Type | Reason                        |
| ------------ | ----------- | ----------------------------- |
| <subtask-id> | <worker>    | <selection rule that matched> |

### Capacity Status

[Per-worker-type: current/max from WORKERS.md]
```

---

### 4.4 Post-Dispatch (fire and forget)

**The supervisor does not actively monitor workers.** After dispatch, the
supervisor's job is done. Workers are autonomous — they work, push, and
create PRs. The next touchpoint is when PRs arrive on GitHub.

**Stale task cleanup** (periodic, not real-time):

```bash
# Reset tasks stuck in_progress for >4 hours (cron or manual)
polecat reset-stalled --hours 4 --dry-run
polecat reset-stalled --hours 4
```

This is a janitorial operation, not active supervision. Run it periodically
(e.g., via `stale-check` cron hook) to clean up crashed workers.

**Worker failures surface as missing PRs.** If a worker fails, no PR appears.
The task stays `in_progress` until the stale-check resets it to `active` for
the next dispatch cycle. No supervisor intervention needed.

**Known issue: auto-finish override loop.** When a task was already completed
by another worker (e.g., Jules fixed it), polecat auto-finish detects zero
changes and resets to active, creating an infinite retry loop. Workaround:
mark the task `done` and kill the swarm. See `aops-fdc9d0e2`.

---

### 4.5 Parallel Execution Coordination

Workers coordinate through the task system, not through the supervisor:

**Dependency Respect**:

- Workers only claim tasks with satisfied `depends_on`
- `claim_next_task()` API enforces this automatically
- No supervisor verification needed at runtime

**Conflict Prevention**:

- Each polecat worker operates in isolated worktree
- No two workers touch same task (atomic claiming)
- Jules sessions are isolated by design (separate Google infrastructure)
- If decomposition reveals shared files:
  - Add explicit `depends_on` between subtasks before dispatch

**Batch isolation** (workaround until `aops-2e13ecb4` is fixed):

- `polecat swarm` claims ANY ready task in the project, not just the
  curated batch
- Mark non-batch tasks as `waiting` status before dispatch to prevent
  accidental claiming
- Restore to `active` after the swarm finishes
