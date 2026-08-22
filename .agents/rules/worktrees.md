---
trigger: always_on
description: Prevent creating git worktrees, clones, or subagent scratch directories inside the repository.
---

- **No In-Repo Worktrees or Subagent Directories:** NEVER create git worktrees, temporary clones, or subagent scratch directories inside the repository or under `.agents/`.
- **External Worktree Location:** Place all isolated git worktrees, polecat workspaces, and temporary agent directories in an external location outside the repository root (e.g. `$POLECAT_HOME/worktrees`).
