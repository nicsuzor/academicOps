---
name: q
category: instruction
description: Queue a task for later execution by creating a bd issue
allowed-tools: Bash, Read, Grep
permalink: commands/q
---

# /q - Queue for Later

**Purpose**: Capture a task for later execution as a beads issue.

## Workflow

1. Review the current session for context about what needs to be done
2. Search for related existing issues: `bd list --status=open`
3. **If related issue exists**: Add a checklist item or comment to the existing issue
4. **If no related issue**: Create a new issue using `bd create`
5. DO NOT execute the task. It will be queued for execution later.

## Commands

### Search for existing issues
```bash
bd list --status=open | grep -i "keyword"
bd show <issue-id>  # View details of specific issue
```

### Create new issue
```bash
bd create --title="Task description" --type=task --priority=2
```

**Priority levels**: 0-4 or P0-P4
- 0/P0: Critical (urgent, blocking)
- 1/P1: High (important, soon)
- 2/P2: Medium (default, normal workflow)
- 3/P3: Low (nice to have)
- 4/P4: Backlog (someday/maybe)

**Issue types**: task, bug, feature, epic

### Update existing issue
```bash
# Add to issue description or create a dependent task
bd create --title="Subtask description" --type=task --priority=2
bd dep add <new-issue-id> <parent-issue-id>  # Make it depend on parent
```

## Key Rules

- Always check for existing related issues first (avoid duplicates)
- Use dependencies for sub-tasks that must wait for parent completion
- Keep titles concise and actionable
- Default to priority=2 (medium) unless user specifies otherwise
- DO NOT start working on the issue - just create it for later
