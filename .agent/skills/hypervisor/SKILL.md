---
name: hypervisor
description: Batch parallel task processing with atomic locking. Spawns multiple worker agents that pull from shared queue without duplication.
triggers:
  - "batch tasks"
  - "parallel processing"
  - "process queue in parallel"
---

# Hypervisor - Batch Parallel Processing

Coordinate multiple parallel agents working on a shared queue with atomic locking to prevent duplicate processing.

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

## Parallel Task Agent Pattern

For executing multiple framework tasks in parallel (e.g., from an epic's children):

```python
# Spawn 4-5 worker agents in parallel
Task(subagent_type="aops-core:worker", model="haiku",
     description="Worker 1: <task-summary>",
     prompt="/pull <task-id-1>",
     run_in_background=True)
# Repeat for each task...
```

### Experiment Results (2026-01-22)

Tested spawning 5 parallel haiku workers on aops framework tasks:

| Metric                | Result     |
| --------------------- | ---------- |
| Spawn success         | 5/5 (100%) |
| Execution success     | 5/5 (100%) |
| Conflicts/collisions  | 0          |
| Commits produced      | 5          |
| Notification delivery | 4/5 (80%)  |

### Known Issues

1. **Notification delays**: Task completion notifications arrive 2-5 minutes late, not real-time
2. **Missing notifications**: ~20% of notifications may not arrive at all
3. **Output file cleanup**: Worker output files at `/tmp/claude/.../tasks/*.output` are cleaned up after completion, making post-hoc analysis difficult
4. **No batch status view**: Must check `git log` or task status individually to verify completions
5. **Worker agents lack MCP tools**: Workers cannot call MCP tools (Outlook, Zotero, memory, calendar, browser). Only file operations, git, and code edits work. Filter queue to MCP-independent tasks before spawning workers. See HEURISTICS.md P#77.

### Monitoring Workarounds

```bash
# Check recent commits for worker output
git log --oneline -10

# Check task completion status directly
mcp__plugin_aops-core_tasks__get_task(id="<task-id>")

# Poll output files while workers run (before cleanup)
tail -f /tmp/claude/-home-nic-writing/tasks/*.output
```

### Recommendations for Improvement

1. **Notification reliability**: Investigate why 20% of notifications fail
2. **Persist worker summaries**: Write completion reports to task body or memory
3. **Batch coordinator**: Add a status aggregator that tracks parallel workers
4. **Output retention**: Keep output files for N minutes after completion

## Gemini CLI Task Offloading

Use Gemini CLI to process mechanical tasks from the queue with YOLO mode (auto-approve all tools).

### Configuration

Gemini has `task_manager` MCP server configured at `~/.gemini/settings.json`. Verify with:

```bash
gemini mcp list
# Should show: ✓ task_manager: ... - Connected
```

### Worker Prompt

Located at `prompts/gemini-task-worker.md`. Key features:

- Atomic claiming via `claim_next_task(caller="gemini")`
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

### Design Improvements (from parallel experiments)

**1. Structured completion summary**

Hypervisor should return aggregated results, not require manual TaskOutput polling:

```json
{
  "workers": [
    {
      "task_id": "aops-f7458c85",
      "status": "success",
      "outcome": "verified complete"
    },
    { "task_id": "aops-45528fa7", "status": "blocked", "reason": "lock file" },
    { "task_id": "aops-2fff499a", "status": "success", "commit": "caecab8b" }
  ],
  "runtime_seconds": 427,
  "total_tokens": 156000
}
```

**2. Pre-flight task validation**

Check task state before spawning workers to avoid wasted tokens:

- Skip tasks already `done` or `cancelled`
- Check for existing lock files
- Report "N tasks skipped (already complete)" upfront

**3. Atomic claiming**

Prevent duplicate work if multiple hypervisors run simultaneously:

```python
def claim_task(task_id: str) -> bool:
    """Returns True if claimed, False if already claimed by another worker."""
    lock_path = Path(f"/tmp/hypervisor/locks/{task_id}.lock")
    try:
        lock_path.touch(exist_ok=False)
        return True
    except FileExistsError:
        return False
```
