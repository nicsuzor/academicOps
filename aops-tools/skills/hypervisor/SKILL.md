---
name: hypervisor
description: Batch parallel task processing with atomic locking. Spawns multiple worker agents that pull from shared queue without duplication.
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
