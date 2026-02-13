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
# Claude worker for specific task
polecat run -p <project>

# Gemini worker for specific task
polecat run -g -p <project>

# Jules (manual invocation - not automated)
# Requires explicit human trigger due to cost
```

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

### 4.4 Progress Monitoring Protocol

**Heartbeat Expectations**:

> **Configuration**: See Heartbeat Expectations in [[WORKERS.md]] for per-worker
> update frequencies and alert thresholds.

Each worker type has configured:

- **Expected Heartbeat**: How often task status should update
- **Alert Threshold**: Silence duration that triggers stall detection

**Monitoring Commands**:

```bash
# Check swarm status
polecat summary

# Analyze specific stalled task
polecat analyze <task-id>

# Reset tasks stuck in_progress for >4 hours
polecat reset-stalled --hours 4 --dry-run
polecat reset-stalled --hours 4
```

**Stall Detection Protocol**:

```markdown
## Supervisor: Handle Stalled Worker

1. Detect: Task in_progress > alert_threshold without update
2. Diagnose:
   - Check task body for error messages
   - Check git status in worktree (if accessible)
   - Check for blocking dependencies that appeared
3. Action based on diagnosis:

| Diagnosis               | Action                             |
| ----------------------- | ---------------------------------- |
| Worker crashed          | Reset task to active, re-dispatch  |
| Task blocked            | Mark task blocked, append reason   |
| Infinite loop suspected | Reset task, add constraint to body |
| Resource exhaustion     | Wait, retry with same worker type  |
| Unknown                 | Reset task, flag for human review  |
```

---

### 4.5 Worker Failure Handling

**Exit Code Semantics** (from `polecat run`):

> **Configuration**: See Exit Code Semantics and Retry Limits in [[WORKERS.md]]
> for exit code meanings and recovery parameters.

Map worker exit codes to supervisor actions:

- **Success (0)**: Proceed to merge phase
- **Task/Setup failures**: Apply retry/block logic per configuration
- **Queue empty**: Normal termination, no action needed
- **Unknown codes**: Escalate to human review

**Failure Recovery Protocol**:

```markdown
## Supervisor: Handle Worker Failure

**Task**: <task-id>
**Worker**: <worker-type>
**Exit Code**: <code>
**Error Output**: <last 50 lines>

### Diagnosis

[Supervisor's analysis of what went wrong]

### Recovery Action

[One of: RETRY, REASSIGN, BLOCK, ESCALATE]

### If RETRY:

- Retry count: [n/max per WORKERS.md Retry Limits]
- Backoff: [per WORKERS.md configuration]

### If REASSIGN:

- Original worker: <type>
- New worker: <type>
- Reason: [capability mismatch, etc.]

### If BLOCK:

- Blocking reason appended to task body
- Status set to 'blocked'
- Surfaced in daily note for human

### If ESCALATE:

- Task assigned to human (assignee='nic')
- Full context preserved in task body
```

---

### 4.6 Parallel Execution Coordination

When multiple workers execute simultaneously, the supervisor ensures:

**Dependency Respect**:

- Workers only claim tasks with satisfied `depends_on`
- `claim_next_task()` API enforces this automatically
- Supervisor verifies before dispatch

**Conflict Prevention**:

- Each worker operates in isolated worktree
- No two workers touch same task (atomic claiming)
- If decomposition reveals shared files:
  - Add explicit `depends_on` between subtasks
  - Or process sequentially

**Progress Aggregation**:

```markdown
## Swarm Progress Report

**Project**: <project>
**Swarm Started**: <timestamp>
**Duration**: <elapsed>

### Completed (ready for merge)

| Task      | Worker   | Duration | PR   |
| --------- | -------- | -------- | ---- |
| subtask-1 | claude-1 | 23min    | #456 |

### In Progress

| Task      | Worker   | Started   | Last Update |
| --------- | -------- | --------- | ----------- |
| subtask-2 | gemini-1 | 10min ago | 2min ago    |

### Pending

| Task      | Blocked By | Est. Start  |
| --------- | ---------- | ----------- |
| subtask-3 | subtask-1  | After merge |

### Summary

- Throughput: 2.6 tasks/hour
- Completion: 1/5 (20%)
- Est. remaining: ~1.5 hours
```
