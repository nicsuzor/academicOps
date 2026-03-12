---
title: Polecat System: Ephemeral Agent Workspaces
type: spec
status: active
tier: polecat
depends_on: []
tags: [spec, polecat, architecture]
---

# Polecat System: Ephemeral Agent Workspaces

## Giving Effect

- [[polecat/cli.py]] - CLI tool (`polecat start`, `polecat finish`, `polecat merge`, etc.)
- [[polecat/manager.py]] - Core library for worktree lifecycle (`claim_next_task`, `setup_worktree`, `nuke_worktree`)
- [[polecat/engineer.py]] - Refinery: merge queue processing and test validation
- [[polecat/validation.py]] - Pre-merge validation checks
- [[polecat/github.py]] - GitHub integration for branch/PR management
- [[polecat/observability.py]] - Metrics and logging for polecat operations
- [[commands/pull.md]] - `/pull` command that claims and executes tasks in polecat worktrees

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
        R1[~/src/repo] -->|Spawns| R2[$POLECAT_HOME/polecat/task-id]
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

- **Location:** `$POLECAT_HOME/polecat/`
- **Structure:** `$POLECAT_HOME/polecat/<task-id>/`
- **Mechanism:** `git worktree` linked to bare mirror repositories.

### Bare Mirror Architecture

Worktrees are spawned from **bare mirror clones** stored in `$POLECAT_HOME/polecat/.repos/`, not from your active development repos in `~/src/`. This provides:

- **Isolation**: Complete decoupling from your dev environment
- **Concurrency**: Bare repos handle unlimited concurrent worktrees
- **Clean state**: Each spawn starts from origin, not local uncommitted changes

```
$POLECAT_HOME/polecat/
├── .repos/                    # Hidden bare mirror repos
│   ├── aops.git               # bare clone of academicOps
│   ├── buttermilk.git         # bare clone of buttermilk
│   └── writing.git            # bare clone of writing
├── crew/                      # Persistent crew worktrees
└── task-abc123/               # worktree spawned from .repos/aops.git
```

**Setup:** Run `polecat init` once to create bare mirrors for all registered projects.

### Mirror Sync Behavior

**Automatic safe sync on spawn**: When creating a new worktree, the system automatically runs a safe sync (`git fetch --all` without `--prune`) to pull the latest commits. This is non-fatal - if the sync fails (e.g., offline), the worktree creation continues using the existing mirror state, with a warning.

**Manual sync with `polecat sync`**: This command runs `git fetch --all --prune` which removes stale refs. **Warning**: Running `polecat sync` while worktrees are active may cause issues if it prunes refs that active worktrees depend on. Prefer to run `polecat sync` only when no polecats are running.

**Freshness check**: On worktree creation, the system compares the mirror's main branch to the local repo's main branch. If the mirror is stale (commits behind), a warning is logged but creation proceeds.

## Components

### 1. Polecat Manager (`manager.py`)

A Python library that handles the lifecycle:

- **`claim_next_task(caller, project)`**:
  - Finds the highest priority `active` task.
  - Atomically locks it and updates status to `in_progress`.
  - Assigns it to the caller (e.g., `nic`, `bot`).
- **`setup_worktree(task)`**:
  - Performs a safe sync of the mirror (if used) before creating the worktree.
  - Checks mirror freshness and warns if stale.
  - Identifies the correct parent repo (e.g., `academicOps`, `buttermilk`).
  - Creates a `git worktree` at `$POLECAT_HOME/polecat/<task-id>`.
  - Creates a feature branch `polecat/<task-id>` from `main`.
- **`nuke_worktree(task_id)`**:
  - Force-removes the worktree.
  - Deletes the local branch.

### 2. CLI Tool (`polecat/cli.py`)

The unified interface for worktree management and merging:

```bash
# One-time setup: create bare mirrors for all projects
polecat init

# Refresh mirrors with latest from origin (WARNING: uses --prune, run only when no polecats active)
polecat sync

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

# Run the Refinery: merge all merge_ready tasks to main
polecat merge

# Full automation: claim → run agent → finish
polecat run -p aops
```

#### The `finish` Command

The `finish` command is the critical transition that marks a task as **ready to merge**:

1. **Validates** uncommitted changes (warns if dirty)
2. **Pushes** the current branch to origin
3. **Updates** task status from `in_progress` → `merge_ready`
4. **Optionally** nukes the worktree with `--nuke`

This explicit command ensures workers intentionally signal completion rather than accidentally triggering merge through cleanup.

#### The `merge` Command

The `merge` command runs the Refinery to process all tasks in `merge_ready` status:

1. **Scans** for tasks with `status: merge_ready`
2. **Fetches** and squash-merges each polecat branch to main
3. **Runs tests** after merge
4. **Marks** task as `done` on success
5. **Cleans up** the branch and worktree

On failure, the task status is set to `review` for manual intervention.

#### The `run` Command

The `run` command automates the polecat setup cycle:

1. **Claims** the next ready task (or a specific task with `-t`)
2. **Creates** the worktree
3. **Runs** `claude -p "/pull <task-id>"` in the worktree
4. **Reports** exit status (agents should call `polecat finish` themselves when ready)

```bash
polecat run -p aops              # Run next ready task from aops
polecat run -t task-123          # Run specific task
```

Note: Agents are responsible for calling `polecat finish` at the end of their workflow to mark work as ready for merge. This ensures agents explicitly signal completion rather than having it triggered automatically.

## Workflow

1. **Start:** `polecat start` claims a task (e.g., `osb-c36de7ec`).
2. **Context Switch:** The user/agent `cd`s to `/home/nic/polecats/osb-c36de7ec`.
3. **Work:** Code changes are made, tested, and committed in this isolated environment.
4. **Finish:** `polecat finish` pushes the branch and marks the task as `merge_ready`.
5. **Cleanup:** `polecat nuke` removes the worktree directory.
6. **Merge:** The Refinery scans `merge_ready` tasks, merges them to `main`, and marks them `done`.

### Task Status Lifecycle

```
active → in_progress → merge_ready → done
         (claimed)     (finish)      (merged)
                    ↘ review (on failure)
```

- **active**: Task is ready to be claimed by a worker
- **in_progress**: Worker is actively working on the task
- **merge_ready**: Work is complete, branch pushed, ready for automated merge
- **review**: Merge failed, requires human intervention
- **done**: Merged to main, branch cleaned up

## Crew Merge Workflow

Unlike task-bound polecats, **crews** are persistent named worktrees for interactive work.
They don't have `merge_ready` status transitions - merging is manual.

### When to Merge

Merge a crew branch when:

- Interactive work session is complete
- Changes are ready for integration into main
- Crew is no longer needed for ongoing collaboration

### Merge Steps

For each project in the crew (e.g., `$POLECAT_HOME/crew/cheryl/aops`):

0. **Create tracking task** (before starting):
   ```
   mcp__pkb__create_task(
     title="Merge crew/<name> into <project>",
     type="task",
     project="<project>",
     body="Merging crew work. Document conflicts and resolution here."
   )
   ```

1. **Check status**:
   ```bash
   cd $POLECAT_HOME/crew/<name>/<project>
   git status
   git log main..HEAD --oneline  # See commits to merge
   ```

2. **Commit uncommitted changes** (if dirty):
   ```bash
   git add <files>
   git commit -m "feat: describe the changes"
   ```

3. **Merge to main** (from main repo):
   ```bash
   cd ~/src/<project-repo>
   git merge crew/<name>
   ```

4. **Resolve conflicts** if any, then commit

4b. **Document conflicts** (if any occurred):
Update the tracking task body with:

- Which files had conflicts
- How conflicts were resolved (e.g., "combined both feature sets")
- Why certain changes were kept/discarded

5. **Push**:
   ```bash
   git push origin main
   ```

6. **Cleanup** (optional - only after ALL projects merged):
   ```bash
   polecat nuke-crew <name> --force
   ```

7. **Complete tracking task**:
   Mark the task as done. The task body now serves as audit trail for daily summary.

### Multi-Project Crews

Crews can span multiple projects (e.g., cheryl had aops, buttermilk, mediamarkets).
Repeat steps 1-5 for each project before nuking the crew.

## Repository Mapping

Since worktrees depend on a parent repo, the system maps projects to paths:

| Project      | Repository Path     |
| ------------ | ------------------- |
| `aops`       | `~/src/academicOps` |
| `buttermilk` | `~/src/buttermilk`  |
| `writing`    | `~/writing`         |

## Integration with Task System

This system builds _on top_ of the existing Task MCP:

- It consumes tasks via the internal `TaskStorage.get_ready_tasks()` method.
- It updates tasks via `update_task` (status/assignee) MCP tool.
- It does NOT replace the task database; it just provides the **workspace** for executing them.

## Refinery System

The Refinery completes the lifecycle by merging completed work back into the main repository.

### Refinery Components

1. **Engineer (`polecat/engineer.py`)**:
   - **`scan_and_merge()`**: Finds tasks with status `merge_ready`.
   - **`process_merge(task)`**:
     1. Locates the repo using `PolecatManager.get_repo_path`.
     2. Fetches `origin` to find the `polecat/<task-id>` branch.
     3. Checks out `main` and pulls latest.
     4. **Squash Merges** the feature branch (dry run to check conflicts).
     5. **Runs Tests** (default: `uv run pytest`).
     6. Commits and pushes to `main`.
     7. Deletes the feature branch (local & remote).
     8. Updates task status to `done`.
     9. **Nukes** the local worktree via `PolecatManager`.

2. **CLI (unified with polecat)**:
   ```bash
   # Run a single pass of the merge queue
   polecat merge
   ```

### Kickback & Recovery Workflow

If a merge fails (due to conflicts or failing tests), the Refinery implements a "Kickback" logic:

1. **Status Change**: The task status is set to `review`.
2. **Annotation**: A `🏭 Refinery Report` is appended to the task body, containing the error log and timestamp.
3. **Manual/LLM Intervention**: An interactive agent picks up `review` tasks, fixes the code, and sets status back to `merge_ready` to retry.

## User Expectations

The Polecat System is the foundational workspace for autonomous agent work. Users and agents can expect the following behaviors:

1. **Worktree Isolation**: Every task claimed via `polecat start` or `polecat run` operates in a dedicated, isolated git worktree at `$POLECAT_HOME/polecat/<task-id>`.
   - **Test**: Changes made in a polecat worktree are not visible in the main development repository (e.g., `~/src/academicOps`) until they are explicitly merged.
2. **Concurrency**: Multiple agents can work on different tasks in parallel without branch name collisions or file locking issues.
   - **Test**: Two separate `polecat start` commands for different tasks succeed and create two distinct worktrees and branches.
3. **Atomic Task Claiming**: The system prevents race conditions where two agents attempt to work on the same task simultaneously.
   - **Test**: If two processes call `claim_next_task` for the same task, only one succeeds; the other either picks the next task or returns `None`.
4. **Automatic Branch Management**: Starting a task automatically creates a feature branch named `polecat/<task-id>` from the latest state of the main branch.
   - **Test**: Running `git branch` inside a new polecat worktree shows the correct branch name and its upstream set to `origin/main`.
5. **Verified Merging (Refinery)**: The `polecat merge` command only integrates work that passes the project's automated test suite.
   - **Test**: A task in `merge_ready` status with failing tests is moved to `review` status with an error report, and is NOT merged into `main`.
6. **Clean Exit**: Completing a task with `polecat finish --nuke` or `polecat nuke` removes the worktree and cleans up local resources.
   - **Test**: After `polecat nuke <task-id>`, the directory `$POLECAT_HOME/polecat/<task-id>` no longer exists.
7. **Mirror Freshness**: Worktrees are spawned from a local bare mirror that is automatically synced (best-effort) on creation.
   - **Test**: `polecat start` logs a warning if the local mirror is stale compared to the main development repository, but still completes the setup.
