---
id: bd-workflow
category: operations
---

# BD Issue Tracking Workflow

## Overview

Standard workflow for tracking work in bd (beads) issue tracker. Ensures all work is tracked, visible, and properly closed.

## When to Use

Use this workflow at the beginning and end of any tracked work:
- Feature development
- Bug fixes
- Planning and design work
- Batch operations
- Any work that requires tracking and accountability

## When NOT to Use

Skip bd tracking for:
- Simple questions (information only)
- Direct skill invocations (skills handle their own tracking)
- QA verification (spawned as part of feature work)
- Debugging sessions (investigation phase, not implementation)

## Steps

### 1. Check for existing issues

Check if relevant work already exists:

```bash
bd ready                    # Show issues ready to work
bd list --status=open       # All open issues
```

Search for related issues using keywords from the user's request.

### 2. Create issue if needed

If no matching issue exists, create one:

```bash
bd create --title="Brief description" --type=feature --priority=2
```

Issue types: `feature`, `bug`, `chore`, `docs`
Priority: `0` (critical) to `3` (low), default `2`

### 3. Mark issue as in-progress

Claim the work:

```bash
bd update <id> --status=in_progress
```

This signals to others that you're working on it.

### 4. Do the work

Execute the main workflow steps. The bd issue provides:
- Context for what needs to be done
- Place to document plan and decisions
- Tracking of work state

### 5. Mark issue complete and sync

When work is finished and pushed:

```bash
bd close <id>                # Mark issue as completed
bd sync                      # Sync bd changes to git
```

**IMPORTANT**: Always `bd sync` before `git push` to ensure issue state is saved.

## Quality Gates

- [ ] Issue exists and is marked in-progress
- [ ] Work is completed and tested
- [ ] Issue is closed with `bd close <id>`
- [ ] Changes are synced with `bd sync`

## Success Metrics

- All significant work has a bd issue
- No orphaned work (work done without tracking)
- Issue states reflect actual work state
- bd synced before every git push
