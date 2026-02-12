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
- **CLI**: Worker spawning via `polecat swarm`

## Lifecycle Phases

```
┌─────────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐    ┌───────┐    ┌─────────┐
│  DECOMPOSE  │───►│  REVIEW  │───►│ APPROVE │───►│ EXECUTE  │───►│ MERGE │───►│ CAPTURE │
│  (agent)    │    │ (agents) │    │ (human) │    │ (workers)│    │(human)│    │ (agent) │
└─────────────┘    └──────────┘    └─────────┘    └──────────┘    └───────┘    └─────────┘
```

### Phase 1: Decompose

The supervisor decomposes large tasks into PR-sized subtasks.

**PR-Sized Definition** (all must be true):
- Estimated effort ≤ 4 hours
- Touches ≤ 10 files
- Single logical unit (one "why")
- Testable in isolation
- Reviewable by human in ≤ 15 minutes

**Decomposition Protocol**:

```markdown
## Supervisor: Decompose Task

1. Read task body and context
2. Identify natural boundaries (files, features, dependencies)
3. Create subtasks using decompose_task():
   - Each subtask passes PR-sized criteria
   - Dependencies explicit in depends_on
   - 3-7 subtasks ideal (>7 suggests intermediate grouping)
4. Append decomposition summary to task body
5. Set task status to 'consensus'
```

**Output Format** (appended to task body):

```markdown
## Decomposition Proposal

### Subtasks
| ID | Title | Estimate | Confidence |
|----|-------|----------|------------|
| subtask-1 | Description | 2h | medium |

### Dependency Graph
subtask-1 -> subtask-2 (blocks)
subtask-1 ~> subtask-3 (informs)

### Information Spikes (must resolve first)
- [ ] spike-1: Question we need answered

### Assumptions (load-bearing, untested)
- Assumption 1

### Risks
- Risk 1 (mitigation: ...)
```

### Phase 2: Multi-Agent Review

Supervisor invokes reviewer agents and synthesizes their feedback before human approval.

**Reviewers**:
| Reviewer | Role | Mandatory | Model |
|----------|------|-----------|-------|
| Custodiet | Authority check: is task within granted scope? | Yes | haiku |
| Critic | Pedantic review: assumptions, logical errors, missing cases | Yes | opus |
| Domain specialist | Subject matter expertise | If task.tags intersect specialist.domains | varies |

---

#### 2.1 Reviewer Invocation Protocol

**Step 1: Prepare Review Context**

Before invoking reviewers, prepare a context document containing:

```markdown
# Review Request: <task-id>

## Original Request
[User's original task description]

## Decomposition Proposal
[The decomposition from Phase 1]

## Files/Scope Affected
[List of files the subtasks will touch]

## Relevant Principles
[Extract relevant AXIOMS/HEURISTICS for this domain]
```

**Step 2: Invoke Reviewers in Parallel**

```python
# Spawn both mandatory reviewers simultaneously
critic_task = Task(
    subagent_type='aops-core:critic',
    model='opus',
    prompt='''Review this decomposition proposal:

<context>
{review_context}
</context>

Check for:
1. Logical errors in the decomposition
2. Untested assumptions about dependencies
3. Missing edge cases or error handling
4. Scope drift from original request
5. PR-sizing violations (>4h, >10 files, multiple "whys")

Return your assessment in this exact format:

## Critic Review

**Reviewing**: [1-line description]

### Issues Found
- [Issue]: [why it's a problem]

### Untested Assumptions
- [Assumption]: [why it matters if wrong]

### Verdict
[PROCEED / REVISE / HALT]

[If REVISE or HALT: specific changes needed]
''',
    description='Critic review of decomposition'
)

custodiet_task = Task(
    subagent_type='aops-core:custodiet',
    model='haiku',
    prompt='''Verify this task is within granted authority:

<context>
{review_context}
</context>

Check:
1. Does the decomposition stay within the original request scope?
2. Are there any scope expansions not explicitly authorized?
3. Do any subtasks assume permissions not granted?

Output exactly: OK, WARN, or BLOCK (see custodiet format spec)
''',
    description='Authority verification'
)
```

**Step 3: Collect and Parse Responses**

Wait for both reviewers (timeout: 5 minutes each).

Parse responses into structured verdicts:

| Critic Verdict | Custodiet Verdict | Combined Result |
|----------------|-------------------|-----------------|
| PROCEED | OK | → APPROVED |
| PROCEED | WARN | → APPROVED (log warning) |
| REVISE | OK/WARN | → NEEDS_REVISION |
| HALT | any | → BLOCKED |
| any | BLOCK | → BLOCKED |

---

#### 2.2 Verdict Synthesis Protocol

**On APPROVED**:

```markdown
## Review Synthesis

**Verdict**: APPROVED

### Reviewer Summary
| Reviewer | Verdict | Key Points |
|----------|---------|------------|
| Critic | PROCEED | [1-line summary] |
| Custodiet | OK | Within scope |

### Minor Suggestions (optional)
- [Any non-blocking improvements from reviewers]

→ Proceeding to human approval gate (status='waiting')
```

Then:
```python
update_task(id=task_id, status='waiting', body=synthesis_markdown)
```

**On NEEDS_REVISION**:

```markdown
## Review Synthesis

**Verdict**: NEEDS_REVISION

### Issues Requiring Resolution
1. [Issue from critic]: [specific problem]
   - **Suggested fix**: [how to address]

2. [Issue from custodiet if WARN]: [scope concern]
   - **Suggested fix**: [how to narrow scope]

### Required Actions
- [ ] Address issue 1
- [ ] Address issue 2
- [ ] Re-run review after changes

→ Returning to decomposition (status='decomposing')
```

Then:
```python
update_task(id=task_id, status='active', body=synthesis_markdown)
# Re-enter Phase 1 with reviewer feedback
```

**On BLOCKED**:

```markdown
## Review Synthesis

**Verdict**: BLOCKED

### Blocking Issues
| Reviewer | Issue | Principle Violated |
|----------|-------|-------------------|
| [reviewer] | [issue] | [A#X or H#X] |

### Resolution Required
[Specific action needed before this can proceed]

→ Escalating to human (status='blocked')
```

Then:
```python
update_task(id=task_id, status='blocked', body=synthesis_markdown)
```

---

#### 2.3 Debate Resolution (When Reviewers Disagree)

If reviewers return conflicting verdicts (one PROCEED, one REVISE), initiate a debate round.

**Debate Protocol** (max 2 rounds):

```markdown
## Debate Round 1

### Conflicting Assessments
- **Critic** says PROCEED: "[rationale]"
- **Custodiet** says WARN: "[concern]"

### Resolution Attempt
```

```python
# Share concerns with the other reviewer
debate_task = Task(
    subagent_type='aops-core:critic',
    model='opus',
    prompt='''The custodiet raised this concern about the decomposition:

<concern>
{custodiet_concern}
</concern>

Your original assessment was PROCEED. Given this new information:

1. Do you MAINTAIN your PROCEED verdict?
2. Do you REVISE to account for this concern?

Respond with:
- MAINTAIN: [brief justification]
- REVISE: [what changes you now recommend]
''',
    description='Debate: critic response to custodiet concern'
)
```

**Debate Outcomes**:

| Round Result | Action |
|--------------|--------|
| Both reviewers align | Use aligned verdict |
| Still conflicting after 2 rounds | Synthesize for human decision |

**Synthesizing Unresolved Debates**:

```markdown
## Review Synthesis

**Verdict**: ESCALATE_TO_HUMAN

### Unresolved Reviewer Disagreement

**Critic Position** (after debate):
[Their final position]

**Custodiet Position** (after debate):
[Their final position]

### Core Tension
[Supervisor's 1-sentence summary of why they disagree]

### Options for Human
1. **Proceed as planned**: Accept critic's assessment
2. **Narrow scope**: Accept custodiet's constraint
3. **Request more info**: Specific question to resolve

→ Awaiting human decision (status='waiting')
```

---

#### 2.4 Domain Specialist Invocation (Optional)

When task tags indicate specialized domain expertise is needed:

```python
# Check if domain specialist is warranted
domain_specialists = {
    'security': 'security-reviewer',
    'database': 'db-reviewer',
    'api': 'api-reviewer',
    'frontend': 'ui-reviewer'
}

matching_domains = [d for d in task.tags if d in domain_specialists]

if matching_domains:
    for domain in matching_domains:
        specialist_task = Task(
            subagent_type=f'aops-core:{domain_specialists[domain]}',
            prompt=f'''Review this decomposition for {domain} concerns:

<context>
{{review_context}}
</context>

Focus on {domain}-specific issues:
- Best practices violations
- Security implications (if security domain)
- Performance concerns
- Integration patterns

Return structured feedback.
''',
            description=f'{domain} specialist review'
        )
```

**Note**: Domain specialists are advisory. Their concerns inform but don't automatically block—supervisor synthesizes their input alongside mandatory reviewers.

### Phase 3: Human Approval Gate

Task waits for human decision. Surfaced via `/daily` skill in daily note.

**User Actions**:
| Action | Task State | Notes |
|--------|------------|-------|
| Approve | → in_progress | Subtasks created, first claimed |
| Request Changes | → decomposing | Feedback attached |
| Send Back | → pending | Assignee cleared |
| Backburner | → dormant | Preserved but inactive |
| Cancel | → cancelled | Reason required |

### Phase 4: Worker Execution

Supervisor dispatches workers based on task requirements. This phase transforms approved decomposition into parallel execution.

---

#### 4.1 Worker Types and Capabilities

| Worker | Capabilities | Cost | Speed | Max Concurrent | Best For |
|--------|-------------|------|-------|----------------|----------|
| `polecat-claude` | code, docs, refactor, test, debug | 3 | 5 | 2 | Most tasks |
| `polecat-gemini` | code, docs, analysis, bulk-ops | 1 | 3 | 4 | High-volume, simpler tasks |
| `jules` | deep-code, architecture, complex-refactor | 5 | 1 | 1 | Critical path, complex logic |

**Capability Definitions**:
- `code`: Standard implementation work
- `docs`: Documentation, comments, README updates
- `refactor`: Code restructuring without behavior change
- `test`: Test writing and updates
- `debug`: Bug investigation and fixes
- `analysis`: Code review, spike investigations
- `bulk-ops`: Repetitive changes across many files
- `deep-code`: Complex algorithms, performance-critical code
- `architecture`: System design changes, API contracts
- `complex-refactor`: Multi-file refactors with behavior preservation

---

#### 4.2 Worker Selection Protocol

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

```python
def select_worker(task) -> str:
    """
    Worker selection decision tree.
    Returns: 'claude', 'gemini', or 'jules'
    """
    # Rule 1: Explicit complexity routing
    if task.complexity == 'needs-decomposition':
        return 'jules'  # Shouldn't reach here, but safety net

    if task.complexity in ['requires-judgment', 'multi-step']:
        return 'claude'

    # Rule 2: Tag-based routing
    high_stakes_tags = {'security', 'api', 'database', 'auth', 'payment'}
    if set(task.tags) & high_stakes_tags:
        return 'claude'

    bulk_tags = {'formatting', 'lint-fix', 'dependency-bump', 'rename'}
    if set(task.tags) & bulk_tags:
        return 'gemini'

    # Rule 3: File count heuristic
    if task.files_affected > 10:
        return 'gemini'  # Bulk operations

    # Rule 4: Effort-based (from decomposition estimate)
    if task.effort and task.effort > '2h':
        return 'claude'

    # Default: Claude for safety
    return 'claude'
```

**Step 3: Check Capacity**

Before dispatch, verify worker availability:

```bash
# Check current worker count (conceptual - supervisor tracks internally)
# active_claude = count of in_progress tasks assigned to 'polecat' with claude flag
# active_gemini = count of in_progress tasks assigned to 'polecat' with gemini flag

# If at capacity, queue for later or wait
```

| Worker | At Capacity Action |
|--------|-------------------|
| claude | Queue task, try gemini if capable |
| gemini | Queue task, wait for slot |
| jules | Queue task (never substitute) |

---

#### 4.3 Dispatch Protocol

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

| Ready Tasks | Task Mix | Recommended Swarm |
|-------------|----------|-------------------|
| 1-2 | Any | `polecat run` (no swarm) |
| 3-5 | Mostly simple | `-c 1 -g 2` |
| 3-5 | Mostly complex | `-c 2 -g 1` |
| 6-10 | Mixed | `-c 2 -g 3` |
| 10+ | Mixed | `-c 2 -g 4` (max reasonable) |

**Dispatch Output Format** (appended to parent task body):

```markdown
## Worker Dispatch Log

**Dispatched**: 2026-02-12T14:30:00Z
**Swarm**: 2 Claude, 3 Gemini

### Task Assignments
| Task | Worker Type | Reason |
|------|-------------|--------|
| subtask-1 | claude | complexity=requires-judgment |
| subtask-2 | gemini | tags=[formatting] |
| subtask-3 | claude | files>10, critical path |

### Capacity Status
- Claude: 2/2 (at limit)
- Gemini: 3/4 (1 slot available)
```

---

#### 4.4 Progress Monitoring Protocol

**Heartbeat Expectations**:

| Worker | Expected Heartbeat | Alert Threshold |
|--------|-------------------|-----------------|
| claude | Task status update every 30min | 45min silence |
| gemini | Task status update every 20min | 30min silence |
| jules | Task status update every 60min | 90min silence |

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

| Diagnosis | Action |
|-----------|--------|
| Worker crashed | Reset task to active, re-dispatch |
| Task blocked | Mark task blocked, append reason |
| Infinite loop suspected | Reset task, add constraint to body |
| Resource exhaustion | Wait, retry with same worker type |
| Unknown | Reset task, flag for human review |
```

---

#### 4.5 Worker Failure Handling

**Exit Code Semantics** (from `polecat run`):

| Exit Code | Meaning | Supervisor Action |
|-----------|---------|-------------------|
| 0 | Success | Mark merge_ready, proceed to Phase 5 |
| 1 | Task failure | Inspect error, mark blocked or retry |
| 2 | Setup failure | Retry once, then mark blocked |
| 3 | Queue empty | Normal - no action needed |
| 4+ | Unknown | Mark blocked, flag for human |

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
- Retry count: [n/3 max]
- Backoff: [exponential, starting 5min]

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

#### 4.6 Parallel Execution Coordination

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
| Task | Worker | Duration | PR |
|------|--------|----------|-----|
| subtask-1 | claude-1 | 23min | #456 |

### In Progress
| Task | Worker | Started | Last Update |
|------|--------|---------|-------------|
| subtask-2 | gemini-1 | 10min ago | 2min ago |

### Pending
| Task | Blocked By | Est. Start |
|------|-----------|------------|
| subtask-3 | subtask-1 | After merge |

### Summary
- Throughput: 2.6 tasks/hour
- Completion: 1/5 (20%)
- Est. remaining: ~1.5 hours
```

### Phase 5: PR Review & Merge

Human gate. Supervisor surfaces merge-ready tasks in daily note.

```markdown
## Ready to Merge

| PR | Task | Tests | Reviews | Summary |
|----|------|-------|---------|---------|
| [#123](url) | [[task-abc]] | Pass | 3/3 APPROVE | Added auth module |
```

**Merge via**:
- `gh pr merge --squash --delete-branch`
- Or GitHub Actions auto-merge for clean PRs

### Phase 6: Knowledge Capture

Post-merge, supervisor extracts learnings.

**Extraction Protocol**:

```markdown
## Supervisor: Capture Knowledge

1. Collect sources:
   - PR description and comments
   - Commit messages
   - Task body
   - Review comments

2. Extract learnings:
   - Decisions made
   - Alternatives rejected
   - Patterns discovered
   - Mistakes caught
   - Estimate accuracy

3. Store via /remember skill

4. Create follow-up tasks if needed:
   - TODO comments → tech-debt task
   - Reviewer suggestions → enhancement task (needs approval)
   - Estimate >50% off → learn task for estimation improvement
```

---

# Parallel Worker Orchestration

Orchestrate multiple parallel polecat workers, each with isolated git worktrees. This replaces the deprecated hypervisor patterns.

## Quick Start

```bash
# Spawn 2 Claude + 3 Gemini workers for aops project
polecat swarm -c 2 -g 3 -p aops

# Dry run to test configuration
polecat swarm -c 1 -g 1 --dry-run
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Swarm Supervisor                       │
│  (polecat swarm command - manages worker lifecycles)    │
└─────────────────────────────────────────────────────────┘
          │                              │
          ▼                              ▼
┌─────────────────────┐    ┌─────────────────────┐
│  Claude Worker 1    │    │  Gemini Worker 1    │
│  CPU affinity: 0    │    │  CPU affinity: 2    │
└─────────────────────┘    └─────────────────────┘
          │                              │
          ▼                              ▼
┌─────────────────────┐    ┌─────────────────────┐
│ Worktree: task-abc  │    │ Worktree: task-xyz  │
│ Branch: polecat/abc │    │ Branch: polecat/xyz │
└─────────────────────┘    └─────────────────────┘
```

### Key Features

1. **Worktree Isolation**: Each worker gets its own git worktree - no merge conflicts
2. **Atomic Task Claiming**: `claim_next_task()` API prevents duplicate work
3. **CPU Affinity**: Workers bound to specific cores for predictable performance
4. **Auto-Restart**: Successful workers restart immediately for next task
5. **Failure Isolation**: Failed workers stop and alert; others continue
6. **Graceful Drain**: Ctrl+C enables drain mode (finish current, don't claim new)

## Usage

### Basic Commands

```bash
# Spawn workers
polecat swarm -c <claude_count> -g <gemini_count> [-p <project>]

# Options:
#   -c, --claude N     Number of Claude workers
#   -g, --gemini N     Number of Gemini workers
#   -p, --project      Filter to specific project
#   --caller           Identity for task claiming (default: bot)
#   --dry-run          Simulate without running agents
#   --home             Override polecat home directory
```

### Workflow

1. **Init mirrors** (one-time setup):
   ```bash
   polecat init
   ```

2. **Sync mirrors** (before spawning):
   ```bash
   polecat sync
   ```

3. **Spawn swarm**:
   ```bash
   polecat swarm -c 2 -g 3 -p aops
   ```

4. **Monitor**:
   - Workers log to stdout with `[CLAUDE-Worker-PID]` or `[GEMINI-Worker-PID]` prefix
   - Desktop notifications on failures (if `notify-send` available)

5. **Stop gracefully**: Press Ctrl+C once for drain mode (finish current tasks)
6. **Force stop**: Press Ctrl+C twice to terminate immediately

### Worker Lifecycle

Each worker runs this loop:

```
claim_task() → setup_worktree() → run_agent() → finish() → [restart or exit]
```

On success (exit 0): Worker restarts immediately for next task
On failure (exit != 0): Worker stops, alerts, others continue

## When to Use

| Scenario              | Use This                           |
| --------------------- | ---------------------------------- |
| 10+ independent tasks | `polecat swarm`                    |
| Single task           | `polecat run`                      |
| Interactive work      | `polecat crew`                     |
| Non-task batch ops    | See hypervisor atomic lock pattern |

## Comparison with Deprecated Patterns

| Feature    | Old Hypervisor      | New Swarm              |
| ---------- | ------------------- | ---------------------- |
| Worktree   | Shared (conflicts!) | Isolated per task      |
| Claiming   | File locks          | API-based atomic claim |
| Workers    | `Task()` subagents  | Native processes       |
| Restart    | Manual              | Automatic on success   |
| Monitoring | Poll TaskOutput     | Native stdout/alerts   |

## Troubleshooting

### "No ready tasks found"

- Check task status: tasks must be `active` and have no unmet dependencies
- Verify project filter matches existing tasks

### Worker keeps failing

1. Check the specific error in worker output
2. Look for task-specific issues (missing files, invalid instructions)
3. Mark problematic task as `blocked` and restart

### Stale locks after crash

```bash
# Reset tasks stuck in_progress for >4 hours
polecat reset-stalled --hours 4

# Dry run first
polecat reset-stalled --hours 4 --dry-run
```

### Merge conflicts

Shouldn't happen with worktree isolation. If it does:

1. Check if multiple tasks modify same files
2. Add `depends_on` relationships between them
3. Or process sequentially instead of in parallel

## Supervisor Session Efficiency

Supervisor sessions consume context quickly. Minimize by:

### Use Batch Commands

```bash
# Check status in one command
polecat summary

# Merge all clean PRs at once (when available)
gh pr list --json number -q '.[].number' | xargs -I{} gh pr merge {} --squash --delete-branch && polecat sync
```

### Use Watchdog Instead of Polling

```bash
polecat watch &  # Background notifications for new PRs
```

### Commission Don't Debug

When functionality is missing:

1. **Don't write code** - create a task with `/q`
2. Assign to `polecat` with clear acceptance criteria
3. Let swarm implement and file PR
4. Merge and use

This keeps supervisor sessions lean.

### Available Monitoring Commands

```bash
polecat summary              # Digest of recent work
polecat analyze <task-id>    # Diagnose stalled tasks
polecat watch                # Background PR notifications
polecat reset-stalled        # Reset hung in_progress tasks
```

## Refinery Workflow

The "refinery" handles PR review and merge:

### Local Refinery (default)

- Manual merge via `gh pr merge --squash`
- Handle conflicts, complex PRs
- Works for all repos

### GitHub Actions Refinery (aops only)

- Auto-merge clean PRs (pure additions, tests pass)
- Label `polecat` triggers workflow
- Failed checks → stays open for review

## Related

- `/pull` - Single task workflow (what each worker runs internally)
- `polecat run` - Single autonomous polecat (no swarm)
- `polecat crew` - Interactive, persistent workers
- `hypervisor` - Deprecated; atomic lock pattern still useful for non-task batches
- `/q` - Quick-queue tasks for swarm to implement
