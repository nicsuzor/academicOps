---
name: decision-extract
category: instruction
description: Extract pending decisions from task queue, prioritize by blocking count, output to daily note for batch processing.
allowed-tools: Read,Edit,mcp__plugin_aops-core_task_manager__list_tasks,mcp__plugin_aops-core_task_manager__get_task,mcp__plugin_aops-core_task_manager__get_tasks_with_topology
version: 1.0.0
permalink: skills-decision-extract
---

# Decision Extract Skill

Extract pending decisions from your task queue and format them for batch processing in your daily note.

## What is a Decision?

A **decision** is a task that:
- Requires your input/approval but NOT substantive work
- Is blocking other tasks from proceeding
- Can typically be resolved in <5 minutes

**Examples**:
- RSVP yes/no, approve/reject, go/no-go, choose A vs B
- Tasks waiting on external input (you can report progress, follow up, or cancel)

**Not decisions**: Write code, research topic, draft document, fix bug

**Note on external dependencies**: Tasks waiting for others (e.g., "waiting for Elsa's examples") are included because you can still make decisions about them:
- Report progress: "No update yet" / "Received, proceeding"
- Follow up: "Sending reminder"
- Cancel: "No longer needed"

## When to Use

- Run `/decision-extract` when you want to batch-process pending decisions
- The `/daily` skill includes a decision count summary automatically
- Use when feeling overwhelmed by scattered approval requests

## Extraction Logic

### Step 1: Query Decision Tasks

Query tasks that are waiting for your input:

```python
# Get waiting tasks assigned to user
waiting_tasks = mcp__plugin_aops-core_task_manager__list_tasks(
    status="waiting",
    assignee="nic",
    limit=50
)

# Get review tasks assigned to user
review_tasks = mcp__plugin_aops-core_task_manager__list_tasks(
    status="review",
    assignee="nic",
    limit=50
)
```

### Step 2: Filter Non-Decision Types

Exclude high-level planning items that aren't actionable decisions:

```python
EXCLUDED_TYPES = ["project", "epic", "goal"]

decisions = [
    task for task in (waiting_tasks + review_tasks)
    if task.type not in EXCLUDED_TYPES
]
```

### Step 3: Get Blocking Counts

For each decision, determine how many tasks it's blocking:

```python
topology = mcp__plugin_aops-core_task_manager__get_tasks_with_topology()

# Match decision IDs to topology entries to get blocking_count
for decision in decisions:
    entry = find_in_topology(decision.id, topology)
    decision.blocking_count = entry.blocking_count if entry else 0
```

### Step 4: Prioritize

Sort decisions by:
1. `blocking_count` (descending) - decisions blocking most work first
2. `priority` (ascending) - P0 before P1 before P2
3. `created` (ascending) - older decisions first

```python
decisions.sort(key=lambda d: (-d.blocking_count, d.priority, d.created))
```

### Step 5: Classify Priority Tiers

```python
high_priority = [d for d in decisions if d.blocking_count >= 2]
medium_priority = [d for d in decisions if d.blocking_count == 1]
low_priority = [d for d in decisions if d.blocking_count == 0]
```

## Output Format

Generate markdown for the daily note's `## Pending Decisions` section:

```markdown
## Pending Decisions

You have **{total}** decisions pending ({high} high priority).

### High Priority (Blocking Multiple Tasks)

#### D001: {task_title}
- **Task**: `{task_id}`
- **Blocks**: {blocking_count} tasks
- **Context**: {first 200 chars of task body}
- **Created**: {days_ago} days ago

**Decision**: [ ] Approve  [ ] Reject  [ ] Defer
**Notes**: _________________

---

### Medium Priority (Blocking 1 Task)

#### D002: {task_title}
...

### Low Priority (No Dependencies)

#### D003: {task_title}
...

---

**Instructions**: Mark your decisions above, then run `/decision-apply` to process them.

<!-- decision-metadata
decisions:
  - id: D001
    task_id: {task_id}
    decision: null
    processed: false
  - id: D002
    ...
-->
```

## Integration with Daily Note

### Location in Daily Note

Insert the `## Pending Decisions` section immediately after `## Focus`:

```markdown
## Focus
[existing focus content]

## Pending Decisions
[generated decision content]

## Task Tree
[existing tree]
```

### Updating Existing Section

If `## Pending Decisions` already exists in the daily note:
1. Read existing decisions and their annotations
2. Preserve any user annotations (non-null decisions)
3. Add new decisions not already present
4. Remove decisions that are no longer in waiting/review status

Use Edit tool to update, not Write (preserve surrounding content).

## Decision Count for /daily

When `/daily` runs, include a summary in the Focus section:

```markdown
## Focus

[priority dashboard]

**Pending Decisions**: {count} ({high_priority} blocking other work)
→ Run `/decision-extract` to review and process

[rest of focus content]
```

This summary uses the same query logic (Steps 1-3) but only outputs the count, not the full list.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No decisions found | Output "No pending decisions. Your queue is clear." |
| Daily note missing | Create minimal daily note with decisions section |
| Task details unavailable | Include task ID and title only, note "details unavailable" |

## Example Output

```markdown
## Pending Decisions

You have **4** decisions pending (2 high priority).

### High Priority (Blocking Multiple Tasks)

#### D001: Approve authentication provider choice
- **Task**: `aops-abc123`
- **Blocks**: 3 tasks (login-ui, session-mgmt, user-tests)
- **Context**: Options are Auth0 vs Cognito. See comparison doc for trade-offs.
- **Created**: 5 days ago

**Decision**: [ ] Auth0  [ ] Cognito  [ ] Need more info
**Notes**: _________________

---

#### D002: Sign off on API schema v2
- **Task**: `aops-def456`
- **Blocks**: 2 tasks
- **Context**: Breaking changes from v1. Migration path documented.
- **Created**: 3 days ago

**Decision**: [ ] Approve  [ ] Request changes  [ ] Defer
**Notes**: _________________

---

### Low Priority (No Dependencies)

#### D003: Review PR #789 - typo fix
- **Task**: `aops-ghi789`
- **Blocks**: 0 tasks
- **Context**: Single character typo in README
- **Created**: 1 day ago

**Decision**: [ ] Approve  [ ] Skip
**Notes**: _________________

---

**Instructions**: Mark your decisions above, then run `/decision-apply` to process them.
```

## Related Skills

- `/decision-apply` - Process annotated decisions and update tasks
- `/daily` - Includes decision count in morning briefing
- `/pull` - Pull next task to work on (after decisions are cleared)
