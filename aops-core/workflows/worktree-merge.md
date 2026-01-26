---
id: worktree-merge
category: integration
bases: [base-commit]
---

# Worktree Merge Workflow

Merge completed work from polecat worktrees into the main branch.

## When to Use

Use this workflow when:
- A polecat worker has completed its task in a worktree
- Task status is `merge_ready` or `done` and branch exists
- You need to integrate worktree changes into main

## Prerequisites

- Task with polecat branch (`polecat/{task-id}`)
- Branch has commits to merge (check with `git log main..polecat/{task-id}`)
- Main branch is up to date

## Procedure

### 1. Identify Merge Candidates

Find tasks with branches that need merging:

```bash
# List polecat branches
git branch -a | grep polecat

# For each branch, check if unmerged commits exist
git log --oneline main..polecat/{task-id}
```

Alternatively, use the unified CLI or Engineer class:

```bash
# Unified CLI (preferred)
polecat merge
```

```python
# Or programmatically
from polecat.engineer import Engineer
eng = Engineer()
eng.scan_and_merge()  # Scans MERGE_READY status tasks
```

### 2. Pre-Merge Validation

Before merging, verify:

1. **Task status is appropriate** (review or done)
2. **Branch exists** locally or on origin
3. **Commits exist** that aren't in main
4. **Worktree is clean** (no uncommitted changes)

```bash
# Check for unmerged commits
git log --oneline main..polecat/{task-id}

# If empty output: branch is already merged, skip to cleanup
```

### 3. Execute Merge

The standard merge process:

```bash
# Update main
git checkout main
git pull origin main

# Squash merge the polecat branch
git merge --squash polecat/{task-id}

# Commit with task reference
git commit -m "Merge polecat/{task-id}: {task-title}"

# Push
git push origin main
```

### 4. Run Tests

After merge, validate the integration:

```bash
uv run pytest
```

If tests fail:
- `git reset --hard HEAD~1` to undo the merge commit
- Investigate the failure in the original worktree
- Mark task as `blocked` with failure details

### 5. Cleanup

After successful merge:

```bash
# Delete local branch
git branch -D polecat/{task-id}

# Delete remote branch
git push origin --delete polecat/{task-id}

# Remove worktree if exists
git worktree remove ~/polecats/{task-id} --force
```

### 6. Update Task Status

Mark the task complete if not already:

```
mcp__plugin_aops-tools_task_manager__complete_task(id="{task-id}")
```

## Automated Merge (refinery/engineer.py)

The `Engineer.scan_and_merge()` method automates this workflow:

1. Finds all tasks with `status: merge_ready`
2. For each task:
   - Locates the repo path via PolecatManager
   - Fetches from origin
   - Squash merges the polecat branch
   - Runs tests
   - Commits and pushes
   - Cleans up branch and worktree
   - Marks task as done

**Usage:**

```bash
polecat merge
```

Or programmatically:

```python
from polecat.engineer import Engineer
Engineer().scan_and_merge()
```

## Bulk Merge Operations

When merging multiple polecat branches at once (e.g., "merge all polecats"), follow this systematic approach:

### 1. Audit ALL Branches (Local AND Remote)

Local branches may be synced but remote branches can have unmerged work:

```bash
# Check LOCAL polecat branches
git branch --list 'polecat/*' | while read branch; do
  echo "=== $branch ==="
  git log main..$branch --oneline 2>/dev/null || echo "(no commits ahead)"
done

# Check REMOTE polecat branches (critical - often missed!)
for branch in $(git branch -r | grep 'origin/polecat'); do
  commits=$(git log main..$branch --oneline 2>/dev/null | wc -l)
  if [ "$commits" -gt 0 ]; then
    echo "$branch: $commits unmerged commits"
    git log main..$branch --oneline
  fi
done
```

**Common pitfall**: Local branches may show "no commits ahead" because they were already merged locally, but corresponding remote branches may have additional commits pushed after the local merge.

### 2. Handle Worktrees Before Branch Deletion

Branches attached to worktrees cannot be deleted:

```bash
# List worktrees
git worktree list

# Remove worktrees first (for completed work only!)
git worktree remove ~/polecats/{task-id}

# Then delete the branch
git branch -d polecat/{task-id}
```

### 3. Force Delete After Verification

If `-d` refuses because remote isn't merged but HEAD is:

```bash
# Safe if you've verified the commits are in main
git branch -D polecat/{task-id}
```

### 4. Query Task Status

Check if any tasks are awaiting review:

```bash
# Via MCP tool
mcp__plugin_aops-tools_task_manager__list_tasks(status="merge_ready")

# Or search for polecat-related tasks
mcp__plugin_aops-tools_task_manager__search_tasks(query="polecat")
```

**Note**: Task assignees use `nic` (human) or `bot` (agent), not "engineer".

## Edge Cases

### Branch Already Merged

If `git log main..polecat/{task-id}` returns empty:
- Branch commits are already in main
- Skip merge, proceed directly to cleanup
- This happens when work was cherry-picked or merged manually

### Merge Conflicts

If squash merge fails with conflicts:
1. `git merge --abort`
2. Set task status to `blocked`
3. Add conflict details to task body
4. Human must resolve manually

### Missing Worktree

If the worktree directory doesn't exist but branch does:
- Worktree was already removed
- Proceed with branch merge and cleanup
- This is normal for completed tasks

## Constraints

- Never force-push to main
- Always run tests after merge
- Never skip cleanup steps
- Update task status after merge

## Related

- [[batch-task-processing]] - Spawning polecat workers
- [[handover]] - Session handover includes merge check
- `refinery/refinery/engineer.py` - Automated merge implementation
