---
title: Polecat Supervision Workflow
status: active
created: 2026-02-06
updated: 2026-02-06
implements:
  - swarm-supervisor skill
  - refinery workflow
---

# Polecat Supervision Workflow

Specification for supervising polecat swarm workers: task commissioning, PR merging, and refinery operations.

## Overview

The polecat swarm executes tasks autonomously. Supervision handles:

1. **Task commissioning**: Creating tasks for swarm to implement
2. **PR review/merge**: Merging worker output from GitHub PRs
3. **Refinery operations**: Handling merge conflicts, stale branches, failures

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     TASK QUEUE (MCP)                            │
│  Ready tasks: leaf, status=active, assignee=polecat                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ claim_next_task()
┌─────────────────────────────────────────────────────────────────┐
│                     POLECAT SWARM                               │
│  N Claude + M Gemini workers                                    │
│  Each: claim → worktree → implement → commit → PR               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ gh pr create
┌─────────────────────────────────────────────────────────────────┐
│                     GITHUB PRs                                  │
│  Branch: polecat/<task-id>                                      │
│  Label: polecat (for auto-merge)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     REFINERY                                    │
│  Local: Manual merge via gh pr merge                            │
│  GHA: Auto-merge clean PRs (aops repo only)                     │
└─────────────────────────────────────────────────────────────────┘
```

## Task Commissioning

### When to Commission (vs. Code Manually)

**Commission** (create task for swarm):
- New feature/command
- Bug fix in known location
- Documentation update
- Refactoring with clear scope

**Code manually** (in current session):
- One-line fix
- Urgent blocker requiring immediate fix
- Exploratory work with unclear scope

### Task Creation Pattern

```python
create_task(
    task_title="<clear, actionable title>",
    type="task",  # bug, feature, learn
    project="aops",
    priority=1,  # P0=blocking, P1=high, P2=normal
    assignee="polecat",
    tags=["polecat", "<domain>"],
    body="""# <Title>

## Problem
<What's wrong or missing - 1-2 sentences>

## Solution
<How to fix it>

## Files to Update
- `path/to/file.py`

## Acceptance Criteria
- [ ] Testable criterion 1
- [ ] Testable criterion 2
"""
)
```

### Priority Routing

| Priority | Use When | Example |
|----------|----------|---------|
| P0 | Blocking current work | "polecat watch command" to enable monitoring |
| P1 | High-value workflow improvement | "Auto-merge clean PRs" |
| P2 | Normal backlog | "Add verbose logging flag" |
| P3 | Nice-to-have | "Colorize output" |

## PR Review & Merge

### Merge Criteria

**Auto-merge eligible** (GHA on aops):
- Pure additions (<500 lines)
- Tests pass
- No merge conflicts
- Label: `polecat`

**Manual review required**:
- Deletions >100 lines
- Multiple file types
- Merge conflicts
- Test failures

### Merge Commands

```bash
# Single PR
gh pr merge <N> --repo nicsuzor/academicOps --squash --delete-branch

# Batch merge (all clean PRs)
gh pr list --json number -q '.[].number' | xargs -I{} gh pr merge {} --squash --delete-branch

# After merging, always sync
polecat sync
```

### Red Flags

| Pattern | Indicates | Action |
|---------|-----------|--------|
| `dels > 20000` | Repo nuke (stale mirror) | Close PR, sync mirrors |
| Same +7 lines to file | Stale branch | Close PR |
| Files > 50 with large deletes | Orphan branch | Close PR |

## Refinery Operations

### Local Refinery (all repos)

Interactive merge for:
- Conflicts requiring manual resolution
- Complex PRs needing review
- Non-GitHub worker output

```bash
# Review PR
gh pr view <N> --json additions,deletions,files

# Merge
gh pr merge <N> --squash --delete-branch

# Handle conflict
gh pr checkout <N>
git rebase origin/main
# resolve conflicts
git push --force-with-lease
gh pr merge <N> --squash --delete-branch
```

### GHA Refinery (aops repo only)

Auto-merge via GitHub Actions workflow:

```yaml
# .github/workflows/polecat-auto-merge.yml
on:
  pull_request:
    types: [opened, labeled]
jobs:
  auto-merge:
    if: contains(github.event.pull_request.labels.*.name, 'polecat')
    # ... validate and merge
```

## Monitoring

### Available Commands

```bash
polecat summary              # Digest of recent work
polecat analyze <task-id>    # Diagnose stalled task
polecat watch                # Background PR notifications
polecat reset-stalled        # Reset hung tasks
```

### Watchdog Setup

```bash
# Start background monitoring
polecat watch &

# Options:
#   -i <seconds>    Polling interval (default: 300)
#   -s <minutes>    Stall threshold (default: 30)
#   -p <project>    Filter to project
```

## User Quick Reference

### Start Supervision Session

```bash
# 1. Check swarm status
pgrep -f "polecat.*swarm"

# 2. Start watchdog
cd /home/nic/src/academicOps && uv run polecat/cli.py watch &

# 3. When notified of PRs:
gh pr list --repo nicsuzor/academicOps --state open
```

### Merge Cycle

```bash
# Review
gh pr view <N> --json additions,deletions,files | jq

# Merge if clean
gh pr merge <N> --squash --delete-branch

# Sync mirrors
polecat sync
```

### Commission New Feature

```bash
# Use /q command or create_task directly
/q bot P1 Add polecat dashboard command
```

### End Session

```bash
# Check final status
polecat summary

# Stop swarm if needed
pkill -INT -f "polecat.*swarm"
```

## Related

- [[skills/swarm-supervisor/SKILL.md]] - Skill instructions
- [[commands/q.md]] - Quick queue command
- [[polecat/cli.py]] - CLI implementation
