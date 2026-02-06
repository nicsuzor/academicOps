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
---

# Swarm Supervisor - Parallel Polecat Orchestration

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

| Scenario | Use This |
|----------|----------|
| 10+ independent tasks | `polecat swarm` |
| Single task | `polecat run` |
| Interactive work | `polecat crew` |
| Non-task batch ops | See hypervisor atomic lock pattern |

## Comparison with Deprecated Patterns

| Feature | Old Hypervisor | New Swarm |
|---------|---------------|-----------|
| Worktree | Shared (conflicts!) | Isolated per task |
| Claiming | File locks | API-based atomic claim |
| Workers | `Task()` subagents | Native processes |
| Restart | Manual | Automatic on success |
| Monitoring | Poll TaskOutput | Native stdout/alerts |

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
2. Assign to `bot` with clear acceptance criteria
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
