# Task Triage Workflow

Interactive workflow for cleaning up, prioritizing, and organizing task backlogs.

## When to Use

- Backlog has grown unwieldy (50+ active tasks)
- Decentralized work has created duplicates or obsolete tasks
- Need to consolidate overlapping epics
- Periodic maintenance (weekly/monthly)

## Prerequisites

- Access to task manager MCP tools
- Human available for approval decisions

## Phase 1: Assessment

### Step 1.1: Get Metrics

```
get_graph_metrics()
```

Key numbers to note:

- `total_tasks` - overall scale
- `tasks_by_status` - distribution of active/blocked/done
- `orphan_count` - tasks without parent relationships
- `max_depth` / `avg_depth` - tree structure health

### Step 1.2: Sample Problem Patterns

Query tasks by category to identify patterns:

```python
# Active tasks by project
list_tasks(status="active", project="aops", limit=30)

# Blocked tasks (may need unblocking or closing)
list_tasks(status="blocked", limit=15)

# Review queue (awaiting human decision)
list_tasks(status="review", limit=15)

# Learning tasks (observations, may already be "done")
list_tasks(type="learn", status="active", limit=15)
```

### Step 1.3: Identify Patterns

Common problem patterns:

| Pattern                  | Detection                                | Action                           |
| ------------------------ | ---------------------------------------- | -------------------------------- |
| **Duplicates**           | Same title/goal, different IDs           | Cancel one, note in close reason |
| **Superseded**           | Old task replaced by epic                | Cancel with "superseded by X"    |
| **Stale**                | "TODAY" or date-specific from weeks ago  | Cancel as stale                  |
| **Learning tasks**       | type=learn, observation already captured | Mark done                        |
| **Orphan epics**         | Multiple overlapping epics               | Merge under one parent           |
| **Blocked indefinitely** | No clear unblock path                    | Cancel or re-scope               |

## Phase 2: Interactive Triage

Present tasks in batches for human approval. Use this format:

```markdown
## Triage Batch N: [Category]

| # | ID        | Title      | Recommendation       | Reason       |
| - | --------- | ---------- | -------------------- | ------------ |
| 1 | `task-id` | Task title | **CLOSE/KEEP/MERGE** | Brief reason |
| 2 | ...       | ...        | ...                  | ...          |

**Reply with numbers**: e.g., "approve 1,2,3" or "all" or "skip"
```

### Batch Categories

1. **Quick Wins** - Obvious stale/duplicate tasks
2. **Epic Overlap** - Consolidation candidates
3. **Blocked Tasks** - Unblock or cancel decisions
4. **Learning Tasks** - Mark done if captured
5. **Low Priority (P2+)** - Deprioritize or close

### Alternative: Checklist Format

For faster triage, use checkbox format:

```markdown
### A. LEARN tasks - mark DONE?

1. [ ] `task-id`: Brief description
2. [ ] `task-id`: Brief description

### B. DUPLICATES - cancel?

3. [ ] `task-id`: Dup of `other-id`

Reply: "done: 1,2 cancel: 3,4"
```

## Phase 3: Execute Decisions

For each approved action:

### Close as Cancelled

```python
update_task(
    id="task-id",
    status="cancelled",
    body="## Close Reason\n[Reason: stale/duplicate/superseded]"
)
```

### Close as Done (Learning)

```python
update_task(
    id="task-id",
    status="done",
    body="## Close Reason\nLearning captured. [Brief note]"
)
```

### Merge Under Parent

```python
update_task(
    id="child-id",
    parent="parent-id",
    body="## Triage Note\nMerged under parent [parent-id] - [reason]"
)
```

### Mark as Superseded

```python
update_task(
    id="old-id",
    status="cancelled",
    body="## Close Reason\nSuperseded by [new-id] - [brief explanation]"
)
```

## Phase 4: Verify

After triage session, verify results:

```python
get_graph_metrics()  # Compare to Phase 1 numbers
```

Expected outcomes:

- Fewer active tasks
- Fewer orphans (better parent relationships)
- Cleaner status distribution

## Session Template

```markdown
# Triage Session [DATE]

## Starting State

- Total tasks: X
- Active: Y
- Orphans: Z

## Actions Taken

- Closed as stale: [count]
- Closed as duplicate: [count]
- Merged: [count]
- Marked done (learning): [count]

## Ending State

- Total tasks: X
- Active: Y (delta)
- Orphans: Z (delta)

## Patterns Observed

- [Pattern 1]
- [Pattern 2]

## Follow-up Needed

- [Any tasks requiring deeper review]
```

## Priority Scoring (Future Enhancement)

For advanced prioritization, score tasks on:

1. **Blocking score** - How many tasks depend on this?
2. **Knowledge unlock** - Does completing this reduce uncertainty elsewhere?
3. **Goal alignment** - Explicit link to active project/goal?
4. **Recency** - When was this last referenced in a session?
5. **Effort/impact** - Quick wins vs long slogs

Composite priority = weighted average of dimensions.

## Related Workflows

- `decompose.md` - Breaking down large tasks
- `daily.md` - Daily note and prioritization
- `handover.md` - Session completion

## Changelog

- 2026-02-08: Initial version based on interactive triage session
