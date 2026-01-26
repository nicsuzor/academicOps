# Polecat System: Ephemeral Agent Workspaces

The Polecat System is a mechanism for highly concurrent, isolated agent work using **git worktrees**. It allows multiple agents to work on different tasks simultaneously without interfering with each other or the main repository.

This system is inspired by the "Gas Town" architecture but adapted for the `academicOps` environment using the existing `task` infrastructure.

```mermaid
flowchart TD
    subgraph POLECAT["Polecat Lifecycle"]
        P1[Claim Task] --> P2[Create Worktree]
        P2 --> P3[Work in Isolation]
        P3 --> P4[Push Branch]
        P4 --> P5[Nuke Worktree]
    end

    subgraph REPO["Repo Structure"]
        R1[~/src/repo] -->|Spawns| R2[~/polecats/task-id]
        R2 -.->|Links back| R1
    end

    subgraph MERGE["Refinery (Future)"]
        M1[Scan for Ready Branches] --> M2[Merge to Main]
        M2 --> M3[Close Task]
    end

    P1 -.->|task ready| T[Task DB]
    P5 -.->|task complete| T
```

## Core Concept: The "Kennel"

Instead of creating temporary clones inside the main repo (which confuses IDEs), we use a centralized directory:

*   **Location:** `~/polecats/`
*   **Structure:** `~/polecats/<task-id>/`
*   **Mechanism:** `git worktree` linked to the parent repository.

## Components

### 1. Polecat Manager (`manager.py`)

A Python library that handles the lifecycle:

*   **`claim_next_task(caller, project)`**:
    *   Finds the highest priority `active` task.
    *   Atomically locks it and updates status to `in_progress`.
    *   Assigns it to the caller (e.g., `nic`, `bot`).
*   **`setup_worktree(task)`**:
    *   Identifies the correct parent repo (e.g., `academicOps`, `buttermilk`).
    *   Creates a `git worktree` at `~/polecats/<task-id>`.
    *   Creates a feature branch `polecat/<task-id>` from `main`.
*   **`nuke_worktree(task_id)`**:
    *   Force-removes the worktree.
    *   Deletes the local branch.

### 2. CLI Tool (`polecat/cli.py`)

The unified interface for worktree management and merging:

```bash
# Start working on the next priority task
polecat start --caller nic --project aops

# Checkout a specific task by ID
polecat checkout <task-id>

# List active polecats
polecat list

# Mark work complete and ready for merge
polecat finish [--no-push] [--nuke]

# Clean up worktree (without marking ready)
polecat nuke <task-id>

# Run the Refinery: merge all review tasks to main
polecat merge
```

#### The `finish` Command

The `finish` command is the critical transition that marks a task as **ready to merge**:

1. **Validates** uncommitted changes (warns if dirty)
2. **Pushes** the current branch to origin
3. **Updates** task status from `in_progress` → `review`
4. **Optionally** nukes the worktree with `--nuke`

This explicit command ensures workers intentionally signal completion rather than accidentally triggering merge through cleanup.

#### The `merge` Command

The `merge` command runs the Refinery to process all tasks in `review` status:

1. **Scans** for tasks with `status: review`
2. **Fetches** and squash-merges each polecat branch to main
3. **Runs tests** after merge
4. **Marks** task as `done` on success
5. **Cleans up** the branch and worktree

On failure, the task is assigned to `engineer` for manual intervention.

## Workflow

1.  **Start:** `polecat start` claims a task (e.g., `osb-c36de7ec`).
2.  **Context Switch:** The user/agent `cd`s to `/home/nic/polecats/osb-c36de7ec`.
3.  **Work:** Code changes are made, tested, and committed in this isolated environment.
4.  **Finish:** `polecat finish` pushes the branch and marks the task as `review` (ready for merge).
5.  **Cleanup:** `polecat nuke` removes the worktree directory.
6.  **Merge:** The Refinery scans `review` tasks, merges them to `main`, and marks them `done`.

### Task Status Lifecycle

```
active → in_progress → review → done
         (claimed)    (finish)  (merged)
```

- **active**: Task is ready to be claimed by a worker
- **in_progress**: Worker is actively working on the task
- **review**: Work is complete, branch pushed, ready for merge
- **done**: Merged to main, branch cleaned up

## Repository Mapping

Since worktrees depend on a parent repo, the system maps projects to paths:

| Project | Repository Path |
|---------|-----------------|
| `aops` | `~/src/academicOps` |
| `buttermilk` | `~/src/buttermilk` |
| `writing` | `~/writing` |

## Integration with Task System

This system builds *on top* of the existing Task MCP:
- It consumes tasks via `get_ready_tasks`.
- It updates tasks via `update_task` (status/assignee).
- It does NOT replace the task database; it just provides the **workspace** for executing them.

## Refinery System: The Merge Engineer

The Refinery completes the lifecycle by merging completed work back into the main repository.

### Components

1.  **Engineer (`polecat/engineer.py`)**:
    *   **`scan_and_merge()`**: Finds tasks with status `review` assigned to `refinery` or unassigned.
    *   **`process_merge(task)`**:
        1. Locates the repo using `PolecatManager.get_repo_path`.
        2. Fetches `origin` to find the `polecat/<task-id>` branch.
        3. Checks out `main` and pulls latest.
        4. **Squash Merges** the feature branch (dry run to check conflicts).
        5. **Runs Tests** (default: `uv run pytest`).
        6. Commits and pushes to `main`.
        7. Deletes the feature branch (local & remote).
        8. Updates task status to `done`.
        9. **Nukes** the local worktree via `PolecatManager`.

2.  **CLI (unified with polecat)**:
    ```bash
    # Run a single pass of the merge queue
    polecat merge
    ```

### Kickback & Recovery Workflow

If a merge fails (due to conflicts or failing tests), the Refinery implements a "Kickback" logic:

1.  **Re-assignment**: The task `assignee` is set to `engineer`.
2.  **Status Preservation**: The task remains in `review` status but is skipped by automated scans.
3.  **Annotation**: A `🏭 Refinery Report` is appended to the task body, containing the error log and timestamp.
4.  **Manual/LLM Intervention**: An interactive agent picks up tasks assigned to `engineer`, fixes the code, and re-assigns back to `refinery` or unassigned to retry.
