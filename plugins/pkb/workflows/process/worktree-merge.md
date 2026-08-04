---
id: worktree-merge
kind: process
category: operations
description: Merge a worktree branch back into the main line once its task is verified and merge_ready
requires: []
pairs-with: [wf-handover]
conflicts: []
version: 1.0.0
permalink: workflows-process-worktree-merge
---

# Process: Worktree Merge

**When to invoke**: after a worker has marked a task `merge_ready` and the PR
has passed all required checks.

## Steps

1. **Verify readiness** — task is `merge_ready`, all PR checks (CI, lint,
   tests) have passed.
2. **Review the PR** — final look at content and reviewer comments.
3. **Merge** — squash merge, delete the branch.
4. **Update the task** — mark `done`.
5. **Sync workspace** — pull in the main worktree.
6. **Cleanup** — remove worktrees no longer needed.

## Critical Rules

- Always squash merge — keeps history clean.
- Delete the feature branch immediately after a successful merge.
- No manual merges without a PR, unless explicitly instructed.
- Never merge with failing CI.
