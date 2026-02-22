---
name: decision-apply
category: instruction
description: Process annotated decisions from daily note, update task statuses, and unblock dependent tasks.
allowed-tools: Read,Edit,mcp__pkb__update_task,mcp__pkb__get_task,mcp__pkb__get_task_network
version: 1.0.0
permalink: skills-decision-apply
---

# Decision Apply Skill

Process your annotated decisions from the daily note and update the task system accordingly.

## Prerequisites

- Run `/decision-extract` first to generate the decisions section
- Annotate your decisions in the daily note (mark checkboxes, add notes)
- Then run `/decision-apply` to execute

## Apply Logic

### Step 1: Locate Daily Note

```python
# Get today's date
today = datetime.now().strftime("%Y%m%d")
daily_note_path = f"$ACA_DATA/daily/{today}-daily.md"
```

Read the daily note using the Read tool.

### Step 2: Parse Decision Section

Find the `## Pending Decisions` section and extract:

1. **Decision metadata block** (YAML in HTML comment):

```markdown
<!-- decision-metadata
decisions:
  - id: D001
    task_id: aops-abc123
    decision: null
    processed: false
-->
```

2. **User annotations** from the decision entries:

- Checked boxes: `[x] Approve`, `[x] Reject`, etc.
- Notes field content

### Step 3: Extract User Decisions

For each decision entry, determine user's choice:

```python
APPROVE_MARKERS = ["[x] Approve", "[x] Yes", "[x] Go"]
REJECT_MARKERS = ["[x] Reject", "[x] No", "[x] Cancel"]
DEFER_MARKERS = ["[x] Defer", "[x] Later"]
SKIP_MARKERS = ["[x] Skip"]
INFO_MARKERS = ["[x] Need more info"]

def parse_decision(entry_text):
    """Parse a single decision entry to extract user's choice."""
    if entry_text is None:
        raise ValueError("entry_text is required")

    # Check approval markers
    for marker in APPROVE_MARKERS:
        if marker in entry_text:
            return "approve"

    # Check rejection markers
    for marker in REJECT_MARKERS:
        if marker in entry_text:
            return "reject"

    # Check defer markers
    for marker in DEFER_MARKERS:
        if marker in entry_text:
            return "defer"

    # Check skip markers
    for marker in SKIP_MARKERS:
        if marker in entry_text:
            return "skip"

    # Check needs-info markers
    for marker in INFO_MARKERS:
        if marker in entry_text:
            return "needs_info"

    # Check for custom decision in Notes field
    notes_match = extract_notes(entry_text)
    if notes_match is not None and notes_match.strip() != "":
        return ("custom", notes_match.strip())

    return None  # No decision made
```

### Step 4: Apply Each Decision

For each decision with a non-null choice:

#### Approve/Yes/Go

```python
mcp__pkb__update_task(
    id=task_id,
    status="active",
    body=f"Decision: Approved by user on {today}. Notes: {notes}"
)
```

#### Reject/No/Cancel

```python
mcp__pkb__update_task(
    id=task_id,
    status="cancelled",
    body=f"Decision: Rejected by user on {today}. Notes: {notes}"
)
```

#### Defer

```python
mcp__pkb__update_task(
    id=task_id,
    status="waiting",  # Keep in waiting
    body=f"Decision: Deferred on {today}. Will revisit. Notes: {notes}"
)
```

#### Skip

```python
# No status change, just mark as processed
# Task stays in current state for next extraction
```

#### Needs More Info

```python
mcp__pkb__update_task(
    id=task_id,
    status="blocked",
    body=f"Decision: Needs more info ({today}). Notes: {notes}"
)
```

#### Custom Decision

```python
mcp__pkb__update_task(
    id=task_id,
    status="active",  # Default to unblocking
    body=f"Decision: {custom_text} ({today})"
)
```

### Step 5: Track Unblocked Tasks

After updating each decision task, check what got unblocked:

```python
def get_newly_unblocked(task_id):
    """Find tasks that were blocked by this decision."""
    task = mcp__pkb__get_task(id=task_id)

    # Tasks in the 'blocks' list are now potentially unblocked
    unblocked = []
    for blocked_id in task.get("blocks", []):
        blocked_task = mcp__pkb__get_task(id=blocked_id)
        # Check if all dependencies are now met
        if all_deps_complete(blocked_task):
            unblocked.append(blocked_task)

    return unblocked
```

### Step 6: Update Daily Note

After processing, update the `## Pending Decisions` section:

1. Mark processed decisions with checkmarks
2. Add processing timestamp
3. List unblocked tasks

```markdown
## Pending Decisions

Processed at 14:30 - 3 decisions applied, 5 tasks unblocked.

### Completed Decisions

- D001: Approved authentication provider - Auth0 selected
  - Unblocked: [aops-login] Login UI, [aops-session] Session mgmt
- D002: Rejected API schema v2 - Requested changes
- D003: Deferred PR review - Will revisit tomorrow

### Still Pending

(None remaining)

---

**Next**: Run `/pull` to start working on unblocked tasks.
```

Use Edit tool to update the section in place.

## Output Report

After processing, output a summary:

```markdown
## Decision Apply Results

**Processed**: 3 of 4 decisions
**Skipped**: 1 (no annotation)

| Decision | Task          | Action               | Unblocked |
| -------- | ------------- | -------------------- | --------- |
| D001     | `aops-abc123` | Approved - active    | 2 tasks   |
| D002     | `aops-def456` | Rejected - cancelled | 0 tasks   |
| D003     | `aops-ghi789` | Deferred - waiting   | 0 tasks   |

**Total tasks unblocked**: 2

- [aops-login] Login UI implementation
- [aops-session] Session management

**Remaining pending decisions**: 1

- D004: PR #789 review (no annotation)

Run `/decision-extract` again to refresh the pending list.
```

## Partial Processing

If user only annotates some decisions:

1. Process all annotated decisions
2. Leave unannotated decisions in the Pending section
3. Report what was processed and what remains
4. Do NOT prompt for missing annotations (trust user intent)

## Safety Rules

### NEVER Auto-Execute

This skill updates task STATUS only. It does NOT:

- Send emails
- Make calendar changes
- Execute code
- Delete files

Those actions require separate skills with explicit user invocation.

### Preserve User Notes

When updating task bodies, APPEND to existing content:

```python
mcp__pkb__update_task(
    id=task_id,
    body=f"## Decision Log\n\n- {today}: {decision_text}",
    replace_body=False  # Append, don't replace
)
```

### Audit Trail

Every decision application adds to the task's body:

- Date of decision
- User's choice
- User's notes (if any)

This creates an audit trail for future reference.

## Error Handling

| Scenario                | Behavior                                                                           |
| ----------------------- | ---------------------------------------------------------------------------------- |
| No decisions section    | Output "No pending decisions found. Run `/decision-extract` first."                |
| Task not found          | Log warning, skip that decision, continue with others                              |
| Invalid decision format | Log warning, skip, continue                                                        |
| All decisions skipped   | Output "No annotations found. Add your decisions to the daily note and run again." |

## Example Session

**Before** (daily note has annotated decisions):

```markdown
#### D001: Approve authentication provider

**Decision**: [x] Auth0 [ ] Cognito [ ] Need more info
**Notes**: Go with Auth0 for better docs and support.
```

**User runs**: `/decision-apply`

**After** (task updated):

```yaml
# Task aops-abc123 now has:
status: active
body: |
  ...existing content...

  ## Decision Log

  - 2026-02-03: Approved (Auth0 selected). Notes: Go with Auth0 for better docs and support.
```

**Output**:

```
Decision Apply Results

Processed: 1 decision
- D001: Approved - task `aops-abc123` now active

Unblocked: 3 tasks
- [aops-login] Login UI implementation
- [aops-session] Session management
- [aops-tests] User auth tests

Run `/pull` to start working on unblocked tasks.
```

## Related Skills

- `/decision-extract` - Generate the pending decisions list
- `/daily` - Morning briefing includes decision count
- `/pull` - Pull next task after decisions are cleared
