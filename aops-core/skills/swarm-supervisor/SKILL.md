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

Supervisor invokes reviewer agents and synthesizes their feedback.

**Reviewers**:
| Reviewer | Role | Mandatory |
|----------|------|-----------|
| Custodiet | Authority check: is task within granted scope? | Yes |
| Critic | Pedantic review: assumptions, logical errors, missing cases | Yes |
| Domain specialist | Subject matter expertise | If task.tags intersect specialist.domains |

**Review Protocol**:

```markdown
## Supervisor: Invoke Reviewers

1. Spawn reviewer subagents in parallel:
   Task(subagent_type='aops-core:critic', prompt='Review decomposition for task <id>')
   Task(subagent_type='aops-core:custodiet', prompt='Verify task <id> is within scope')

2. Wait for all reviewers (10min timeout each)

3. Aggregate verdicts:
   - All APPROVE → status='waiting'
   - Any BLOCK → status='decomposing' (attach feedback)
   - Mixed CONCERN → initiate debate round

4. If debate needed (max 2 rounds):
   - Share all concerns with reviewers
   - Each has 5min to WITHDRAW or MAINTAIN
   - Unresolved concerns → synthesize for human
```

**Reviewer Response Format**:

```yaml
verdict: APPROVE | CONCERN | BLOCK | ESCALATE
rationale: "Why this verdict"
concerns: []  # List of specific issues
suggestions: []  # Optional improvements
```

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

Supervisor dispatches workers based on task requirements.

**Worker Selection**:

```markdown
## Supervisor: Dispatch Worker

1. Identify required capabilities from task tags
2. Select worker type:
   - `polecat-claude`: code, docs, refactor, test (cost: 3, speed: 5)
   - `polecat-gemini`: code, docs, analysis (cost: 1, speed: 3)
   - `jules`: deep-code, architecture, complex-refactor (cost: 5, speed: 1)

3. Check worker availability (max_concurrent limits)

4. Dispatch:
   - Single task: `polecat run -p <project>`
   - Batch: `polecat swarm -c N -g M -p <project>`

5. Monitor progress (30min heartbeat expected)
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
