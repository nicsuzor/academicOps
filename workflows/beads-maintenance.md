---
name: beads-maintenance
title: Beads Maintenance & Triage
category: operations
description: Workflow for organizing, cleaning up, and prioritizing the beads task list
permissions: [read-write]
---

# Beads Maintenance & Triage Workflow

This workflow guides the periodic cleanup and organization of the `bd` task list to ensure it remains a reliable source of truth for work.

## When to use
- When the task list feels cluttered or outdated
- When you need to find work but are overwhelmed by options
- Regular maintenance (weekly/monthly)
- When prompted by the user to "bring some order" to the tasks

## Principles
- **Respect User Tasks**: Issues related to the user (e.g., Nic) must **NOT** be closed for staleness. The user operates on human timescales.
- **Don't modify research tasks**: You can sort and reorder research tasks, but be VERY careful not to change their meaning (even unintentionally).
- **Aggressive Stale Cleanup**: Technical assignments/bugs that are old (3+ months) and where the codebase has changed significantly should be closed.
- **Hierarchy is Key**: Every task should generally belong to an Epic. Use dependencies to model this (`Epic` depends on `Task`).
- **Standard Prefixes**: Ensure tasks have correct prefixes if the project uses them (though `bd` handles IDs, titles should be descriptive).

## Workflow Steps

1. **Prime and List**
   - Run `bd prime` to load the latest state.
   - Run `bd list --status=open` or `bd ready` to see the current inventory.

2. **Triage Candidates**
   - Select a subset of issues to review (e.g., oldest first, or by specific status).
   - Use `bd show <id>` to understand the context of an issue.

3. **Handle Stale Issues**
   - **Check**: Is this a user task? If yes, SKIP.
   - **Check**: Has the codebase changed such that this is irrelevant?
   - **Action**: If executing cleanup, use `bd close <id> --reason="Stale: codebase changed"`.
     - *Note*: If blocked by backward dependencies, use `--force`.

4. **Organize and Categorize**
   - **Link to Epics**: Identify the goals the task supports.
     - Find or create an Epic: `bd list --type=epic` or `bd create --type=epic ...`
     - Link: `bd dep add <epic-id> <task-id>` (The Epic depends on the Task completion).
   - **Update Metadata**:
     - Ensure semantic type is correct: `bd update <id> --type=task|bug|feature`
     - Adjust priority if needed: `bd update <id> --priority=<0-4>`

5. **Sync**
   - Run `bd sync` to persist changes to the remote.

## Common Triage Commands

```bash
# Close multiple stale issues
bd close id1 id2 id3 --reason="Stale cleanup"

# Link task to epic
bd dep add <epic_id> <task_id>

# Check what an issue blocks/depends on
bd show <id>
```
