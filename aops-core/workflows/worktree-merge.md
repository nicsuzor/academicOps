---
id: worktree-merge
category: integration
bases: [base-handover]
triggers: ["merge polecat", "merge polecats", "merge worktrees", "merge ready tasks", "merge branches"]
---

# Worktree Merge Workflow

Merge completed work from polecat worktrees into main.

## When to Use

- Polecat worker has completed its task in a worktree
- Task status is `merge_ready` or `review`
- Need to integrate worktree changes into main

## Procedural Requirements

### Ordering (strict)

1. **Preflight**: Main must be clean (`git status`), list active worktrees
2. **Discover**: List polecat branches, check for unmerged commits, detect already-merged via `git cherry`
3. **Review**: For `review` status tasks — inspect changes, approve or reject before merge
4. **Merge**: One branch at a time, sequential. `git merge --squash`, commit with task reference
5. **Verify**: Run tests AFTER merge, BEFORE cleanup. If tests fail: reset, mark blocked, stop
6. **Cleanup**: Delete branch (local + remote), remove worktree. ONLY after verify passes

### Safety Constraints

- Never force-push to main
- Always run tests after merge, before cleanup
- Cleanup happens AFTER verify, never before — prevents data loss
- One branch at a time for multi-branch merges — verify between each
- Polecats cannot self-merge; reviewer executes merge

### Rejection Workflow

If review finds issues:
- Create task documenting rejection rationale
- Assign back to polecat with specific fix instructions
- Do NOT merge rejected commits

## Automation

Preferred: `polecat merge` CLI handles discovery, merge, tests, and cleanup automatically.

Manual: Follow the strict ordering above.

## Edge Cases

- **Branch already merged**: `git cherry` shows `-` — skip to cleanup
- **Stale worktree**: Large diffs usually indicate staleness, not large changes. Check cherry first.
- **Merge conflicts**: `git merge --abort`, mark task blocked, human resolves
- **No branch for review task**: Refinery failed — reset task to active, reassign to polecat
