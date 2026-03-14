---
id: worktree-merge
name: worktree-merge-workflow
category: operations
bases: [base-handover]
description: Merge worktree branches back into the main development line
permalink: workflows/worktree-merge
tags: [workflow, git, worktree, merge, operations]
version: 1.0.0
---

# Worktree Merge Workflow

**Purpose**: Manage the merging of isolated worktree branches back into the main branch after a task is completed and verified.

**When to invoke**: After a polecat worker has marked a task as `merge_ready` and the PR has passed all required checks.

## Core Workflow Steps

1. **Verify Readiness**: Ensure the task status is `merge_ready` and all PR checks (CI, lint, tests) have passed.
2. **Review PR**: Perform a final review of the PR content and reviewer comments.
3. **Merge Branch**: Use GitHub CLI or web interface to merge the PR.
   ```bash
   gh pr merge <pr-number> --squash --delete-branch
   ```
4. **Update Task**: Once merged, update the task status to `done`.
   ```bash
   mcp__pkb__complete_task(id="<task-id>")
   ```
5. **Sync Workspace**: Run `git pull` in the main worktree to synchronize changes.
6. **Cleanup**: Remove any local worktrees that are no longer needed.
   ```bash
   git worktree remove <path-to-worktree>
   ```

## Critical Rules

- **Squash Merges**: Always use squash merges to keep the main history clean.
- **Delete Branch**: Delete the feature branch immediately after a successful merge.
- **No Manual Merges**: Avoid merging manually without a PR unless explicitly instructed.
- **Verification**: Never merge if CI tests are failing.
