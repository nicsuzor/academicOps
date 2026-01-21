---
id: interactive-triage
category: operations
---

# Interactive Triage Workflow

Triage tasks through interactive discussion with user. Present batches, propose classifications, wait for approval, execute.

## When to Use

- Reviewing newly created tasks for proper filing
- Periodic backlog grooming
- Batch assignment of work to workers
- Epic organization and parent assignment

## When NOT to Use

- Automated worker pipelines (use `/pull`)
- Single-task updates (use task tools directly)
- Emergency work (skip triage)

## Key Steps

1. **Establish baseline**: Get counts, identify stale items
2. **Present batch**: Assess type, project, epic, dependencies, priority, assignee
3. **Get decisions**: Use AskUserQuestion for actionable decisions
4. **Execute approved changes**: Update tasks per user approval
5. **Verify and report**: Confirm changes applied

## Assessment Questions

| Aspect | Question |
|--------|----------|
| **Type** | Correct (task/bug/epic)? |
| **Project** | Has `project:*` label? (REQUIRED) |
| **Epic** | Should be parented to an epic? |
| **Dependencies** | Blocks or depends on other tasks? |
| **Priority** | P0-P3 appropriate? |
| **Assignee** | nic/bot/unassigned? |

## Bot-Readiness Criteria

Task ready for bot assignment when:
- Clear acceptance criteria
- Specific files/locations identified
- Edge cases considered
- No human judgment required

## Sweep Order

1. Stale (30+ days) → close superseded
2. P0 urgent → verify still urgent
3. Human gates → assign to nic
4. Bot-assigned → check blockers valid
5. Clusters → verify sequencing

## Quality Gates

- User explicitly approved changes
- All modified tasks verified
- All triaged tasks have `project:*` label
- Complex work has dependency chains
