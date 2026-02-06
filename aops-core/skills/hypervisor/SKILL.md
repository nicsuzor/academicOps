---
name: hypervisor
description: Atomic locking patterns for batch operations. For parallel task processing, use swarm-supervisor instead.
triggers:
  - "atomic locking"
  - "batch file processing"
  - "file queue processing"
---

# Hypervisor - Atomic Locking Patterns

> **DEPRECATION NOTICE** (2026-02-06): For parallel task processing, use `/swarm-supervisor` and `polecat swarm` instead. The polecat swarm provides:
> - **Worktree isolation** (no merge conflicts)
> - **API-based atomic claiming** (no file locks)
> - **Auto-restart on success**
> - **Graceful drain mode**
>
> This skill is retained only for the **atomic locking pattern** which remains useful for non-task batch operations (e.g., processing a queue of files).

Coordinate batch operations with atomic locking to prevent duplicate processing.

## Pattern

1. **Queue**: List of work items (file paths, task IDs, etc.)
2. **Atomic locks**: `mkdir` creates lock directory - atomic on POSIX, fails if exists
3. **Workers**: Multiple agents claim items, process, report results

## Usage

### 1. Create queue and run batch processor

```bash
# Create queue of files to process
find /path/to/files -name "*.md" > /tmp/batch/queue.txt

# Create lock directory
mkdir -p /tmp/batch/locks /tmp/batch/results

# Run batch worker (each agent claims --batch items)
uv run python $AOPS/aops-tools/skills/hypervisor/scripts/batch_worker.py --batch 50
```

### 2. Spawn parallel agents

Spawn multiple Task agents with `run_in_background=true`, each running the batch worker:

```python
Task(
    subagent_type="Bash",
    model="haiku",
    description="Batch worker N",
    prompt="cd /tmp/batch && python3 batch_worker.py --batch 100",
    run_in_background=True
)
```

### 3. Monitor progress

```bash
uv run python $AOPS/aops-tools/skills/hypervisor/scripts/batch_worker.py --stats
```

## Atomic Locking Pattern

```python
def claim_task(task_id: str) -> bool:
    """Atomically claim a task using mkdir (atomic on POSIX)."""
    lock_dir = Path(f"/tmp/batch/locks/{task_id}")
    try:
        lock_dir.mkdir(exist_ok=False)  # Fails if exists
        return True
    except FileExistsError:
        return False  # Already claimed by another worker
```

## Task Triage Example

The `batch_worker.py` script includes task triage logic:

- **Closure detection**: Tasks with `## Close Reason` or `status: done`
- **Assignee allocation**: `nic` for judgment tasks, `bot` for automatable
- **Wikilink injection**: Adds `[[project]]` links based on frontmatter

```bash
# Process all inbox tasks
find /path/to/tasks/inbox -name "*.md" > /tmp/batch/queue.txt
uv run python $AOPS/aops-tools/skills/hypervisor/scripts/batch_worker.py --batch 300
```

## When to Use

- Processing 50+ items that don't depend on each other
- Operations where duplicate processing would cause problems
- Batch operations that benefit from parallelism

## DEPRECATED: Polecat Herd Management

> **Use `polecat swarm` instead** - see `/swarm-supervisor` skill.
>
> The patterns below are outdated and cause merge conflicts due to shared worktrees.
> The new `polecat swarm` command provides isolated worktrees per task.

<details>
<summary>Legacy documentation (click to expand)</summary>

### 1. Spawn a Herd (DEPRECATED)

Use `polecat run` to spawn autonomous agents. Each process handles its own lifecycle, git operations, and completion.

```bash
# Spawn a Claude (Sonnet) polecat for the 'aops' project
uv run --project ${AOPS} ${AOPS}/polecat/cli.py run -p aops

# Spawn a Gemini polecat (cheaper/faster for mechanical tasks)
uv run --project ${AOPS} ${AOPS}/polecat/cli.py run -p aops -g
```

To spawn a "herd" in parallel (Bash):

```bash
# Spawn 5 Gemini polecats in background
for i in {1..5}; do
  uv run --project ${AOPS} ${AOPS}/polecat/cli.py run -p aops -g &
  sleep 2  # Stagger starts to avoid race conditions on initial lock checks
done
```

### 2. Monitor Status (DEPRECATED)

Check the status of the herd and the worktree:

```bash
# List active polecat processes
pgrep -f "polecat/cli.py"

# Check git status (they all share the worktree, so be careful!)
git status
```

**Note on Isolation**: Polecats run in the *same worktree*. They rely on atomic task claiming (via lockfiles or API) to avoid collisions. If two polecats edit the same file, git merge conflicts may occur.

### 3. Handle Failures (DEPRECATED)

If a polecat gets stuck or crashes:

1. Identify the process ID (`pgrep -a -f polecat`)
2. Kill it (`kill <pid>`)
3. Check for stale lockfiles in `/tmp/hypervisor/locks/` or the task status.

</details>

## DEPRECATED: Gemini CLI Task Offloading

> **Use `polecat swarm -g N` instead** - spawns N Gemini workers with proper isolation.
>
> The manual Gemini CLI patterns below are superseded by swarm integration.

<details>
<summary>Legacy documentation (click to expand)</summary>

### Configuration

Gemini has `task_manager` MCP server configured at `~/.gemini/settings.json`. Verify with:

```bash
gemini mcp list
# Should show: ✓ task_manager: ... - Connected
```

### Worker Prompt

Located at `prompts/gemini-task-worker.md`. Key features:
- Atomic claiming via `list_tasks` + `update_task` (status="in_progress")
- Fail-fast on errors (mark blocked instead of retrying)
- Scope boundaries (no git, no external changes)
- Clear completion/block output format

### Single Task Execution

```bash
# Test run with one task (sandbox mode for safety)
gemini --sandbox -p "@prompts/gemini-task-worker.md Claim and complete one mechanical task from aops project"

# Production run (yolo mode)
gemini --yolo -p "@prompts/gemini-task-worker.md Claim and complete one mechanical task from aops project"
```

### Batch Processing

```bash
# Process multiple tasks sequentially
for i in $(seq 1 5); do
  gemini --yolo -p "@prompts/gemini-task-worker.md Claim and complete one mechanical task from aops project"
done
```

### Verification

```bash
# Check which tasks Gemini completed
grep -l "assignee: gemini" data/aops/tasks/*.md

# Check task completion rate
mcp__plugin_aops-tools_task_manager__get_index_stats --include_projects true
```

### Known Limitations

1. **No MCP tool access**: Gemini cannot use Outlook, Zotero, memory, calendar, browser MCP tools
2. **Sandbox mode requires catatonit**: May fail on systems without this dependency
3. **YOLO mode auto-approves all**: High trust, review git history for rollback
4. **Sequential only**: Gemini CLI doesn't support parallel execution like Claude agents
5. **AfterTool hook errors**: custodiet_gate.py has compatibility issues with Gemini's tool format (non-blocking)
6. **Workspace sandbox**: File access restricted to cwd and .gemini/tmp - run from `$AOPS` root

</details>
