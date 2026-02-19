---
id: worktree-merge
category: integration
bases: [base-handover]
triggers: ["merge polecat", "merge polecats", "merge worktrees", "merge outstanding tasks", "merge ready tasks", "merge branches"]
---

# Worktree Merge Workflow

Merge completed work from polecat worktrees into the main branch.

## Quick Reference (for "merge polecats" requests)

**Primary method** — run the CLI:

```bash
polecat merge
```

This handles discovery, merge, tests, and cleanup automatically.

**If CLI unavailable** — manual checklist (strict order):

1. **Preflight** (before anything else)
   - `git status` — main must be clean
   - `git worktree list` — note active worktrees

2. **Discover** (before creating any task)
   - `git branch -r | grep polecat` — list remote polecat branches
   - For each: `git log --oneline main..origin/polecat/{id}` — check unmerged commits
   - `git cherry main origin/polecat/{id}` — detect already-merged (- = merged)

3. **Task** (based on findings, not assumptions)
   - Check both `merge_ready` AND `review` status tasks
   - If merge candidates exist: claim one (review tasks need inspection first)
   - If none: create task with actual branch list from step 2

4. **Merge** (sequential, one branch at a time)
   - `git checkout main && git pull`
   - `git merge --squash origin/polecat/{id}`
   - `git commit -m "Merge polecat/{id}: {title}"`

5. **Verify** (before any cleanup)
   - `uv run pytest` — tests must pass
   - If fail: `git reset --hard HEAD~1`, mark task blocked, stop

6. **Cleanup** (only after QA passes)
   - `git push origin main`
   - `git branch -D polecat/{id}`
   - `git push origin --delete polecat/{id}`
   - `git worktree remove` (if exists)

**Critical ordering**: Cleanup happens AFTER verify, never before. This prevents data loss.

---

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
5. **Work not already merged** via another path

```bash
# Check for unmerged commits
git log --oneline main..polecat/{task-id}

# If empty output: branch is already merged, skip to cleanup

# Quick check if commits are already in main (different SHAs, same content)
git cherry main polecat/{task-id}
# + = needs merge, - = already in main
```

### 2b. Engineer Review (Human-in-Loop)

For non-trivial merges, the engineer (human or reviewing agent) performs first-pass review:

1. **Analyze each commit**: Read the diff, understand the changes
2. **Check against task requirements**: Does the change satisfy the original task?
3. **Present analysis to human**: Summary, findings, recommendation
4. **Decision gate**: Human approves, rejects, or requests changes

**Rejection workflow**:

- Create task documenting rejection rationale
- Assign task back to the polecat (e.g., `assignee: audre`)
- Include specific fix instructions in task body
- Do NOT merge rejected commits

**Key principle**: Polecats prepare work, reviewers approve, reviewers execute merge. Polecats cannot self-merge.

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

Check for tasks awaiting merge. Look for **both** `merge_ready` AND `review` status:

```bash
# Check merge_ready tasks (ready for immediate merge)
mcp__plugin_aops-core_task_manager__list_tasks(status="merge_ready")

# Check review tasks (pending engineer approval - may also be mergeable)
mcp__plugin_aops-core_task_manager__list_tasks(status="review")
# Or use the dedicated tool:
mcp__plugin_aops-core_task_manager__get_review_tasks(project="")

# Search for polecat-related tasks
mcp__plugin_aops-core_task_manager__search_tasks(query="polecat")
```

**When to merge review vs merge_ready:**

- `merge_ready`: Pre-approved work, merge immediately
- `review`: Requires engineer inspection first. Review the work, then either:
  - Merge if acceptable (update status to done after merge)
  - Reject with feedback (create follow-up task, assign back to polecat)

**User intent clarification**: When user says "merge ready tasks in", they typically mean "process `review` status tasks with oversight". The workflow is:

1. Agent reviews each `review` task
2. Simple/mechanical tasks: agent approves and marks done
3. Complex/judgment tasks: agent asks user for resolution before proceeding

**Note**: Task assignees use `human` (human) or `polecat` (agent), not "engineer".

## Edge Cases

### Branch Already Merged

If `git log main..polecat/{task-id}` returns empty:

- Branch commits are already in main
- Skip merge, proceed directly to cleanup
- This happens when work was cherry-picked or merged manually

Use `git cherry` to detect commits merged via different SHAs:

```bash
git cherry main polecat/{task-id}
# - = already in main (safe to delete branch)
# + = needs merge
```

### Stale Worktrees (Branch Behind Main)

Worktrees can become stale when main moves faster than polecat work:

```bash
# Check how far behind
git log --oneline polecat/{task-id}..main | wc -l
```

**If branch is significantly behind** (e.g., 60+ commits):

1. Check `git cherry` first - work may already be in main
2. If work needs merging: rebase or merge main into branch, then proceed
3. If work is obsolete: delete branch, no merge needed

**Key insight**: Large diffs (100+ files) often indicate staleness, not large changes. The polecat's actual work is usually small; the diff shows main's evolution.

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

### Failed Merge / No Branch (Review Status)

If task is in `review` status but has no branch:

- Refinery may have failed (`git fetch` error, merge conflict, etc.)
- Check task body for "🏭 Refinery Report" section with failure details
- **Work was never completed** - this is NOT a merge candidate

**Resolution**:

1. Reset task to `active` status
2. Reassign to `polecat` for fresh attempt
3. Add triage note explaining the reset

This commonly occurs when polecat sessions hit blocking bugs (e.g., hydration gate) and refinery couldn't process.

## Constraints

- Never force-push to main
- Always run tests after merge
- Never skip cleanup steps
- Update task status after merge

## Related

- [[batch-task-processing]] - Spawning polecat workers
- [[base-handover]] - Session handover includes merge check
- `refinery/refinery/engineer.py` - Automated merge implementation
