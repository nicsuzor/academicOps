---
id: merge-conflict
category: integration
bases: [base-commit]
---

# Merge Conflict Resolution Workflow

Resolve merge conflicts and test failures kicked back from the Refinery.

## When to Use

Use this workflow when:
- Task is in `review` status AND assigned to `engineer`
- Task body contains a `🏭 Refinery Report` with failure details
- Automated merge failed due to conflicts or test failures

## Prerequisites

- Task claimed: `status: review`, `assignee: engineer`
- Refinery Report present in task body (contains error details)
- Polecat branch exists: `polecat/{task-id}`

## Procedure

### 1. Identify the Problem

Read the Refinery Report in the task body. Common failure types:

| Error | Cause | Resolution Path |
|-------|-------|-----------------|
| "Merge conflicts detected" | Code diverged from main | Resolve conflicts in worktree |
| "Tests failed" | Feature broke existing tests | Fix code or update tests |
| "Branch not found" | Branch deleted prematurely | Recreate from backup or abandon |

### 2. Setup Worktree (if needed)

If the worktree was nuked, recreate it:

```bash
# From the parent repo
git worktree add ~/polecats/{task-id} polecat/{task-id}
cd ~/polecats/{task-id}
```

### 3. Resolve Conflicts

For merge conflicts:

```bash
# In the worktree, update main reference
git fetch origin main
git merge origin/main

# Resolve conflicts in editor
# Then commit the resolution
git add .
git commit -m "resolve: merge conflicts with main"
git push origin polecat/{task-id}
```

For test failures:

```bash
# Run tests to reproduce
uv run pytest

# Fix the failing tests or code
# Commit fixes
git add .
git commit -m "fix: resolve test failures for merge"
git push origin polecat/{task-id}
```

### 4. Verify Resolution

Before handing back to Refinery:

```bash
# Verify merge will succeed
git fetch origin main
git merge --no-commit --no-ff origin/main
# If clean, abort the test merge
git merge --abort

# Verify tests pass
uv run pytest
```

### 5. Hand Back to Refinery

Update the task to trigger re-merge:

```
mcp__plugin_aops-tools_task_manager__update_task(
  id="{task-id}",
  assignee="",  # Clear assignee so Refinery picks it up
  body="## Resolution ({date})\n\nConflicts resolved. Ready for re-merge."
)
```

The Refinery will automatically retry the merge on its next scan.

### 6. Alternative: Manual Merge

If Refinery keeps failing, complete the merge manually:

```bash
# In the parent repo (not worktree)
cd ~/src/academicOps
git checkout main
git pull origin main
git merge --squash polecat/{task-id}
git commit -m "Merge polecat/{task-id}: {task-title}"
git push origin main

# Cleanup
git branch -D polecat/{task-id}
git push origin --delete polecat/{task-id}
```

Then mark the task done:

```
mcp__plugin_aops-tools_task_manager__complete_task(id="{task-id}")
```

## Decision Tree

```
Task assigned to 'engineer'?
├── No → Not this workflow (use [[worktree-merge]] or run Refinery)
└── Yes → Read Refinery Report
    ├── "Merge conflicts" → Resolve conflicts (Step 3a)
    ├── "Tests failed" → Fix tests (Step 3b)
    └── "Branch not found" → Assess if recoverable
        ├── Recoverable → Recreate branch
        └── Not recoverable → Cancel task, create new one
```

## Constraints

- Never force-push to shared branches
- Always verify tests pass before handing back
- Append resolution notes to task body (audit trail)
- Clear `assignee` field to trigger Refinery retry

## Related

- [[worktree-merge]] - Manual merge process
- `refinery/engineer.py` - Automated merge + kickback logic
- `specs/polecat-system.md` - Polecat lifecycle and Refinery design
