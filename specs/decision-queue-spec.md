---
title: Decision Queue Specification
type: spec
status: active
tier: workflow
depends_on: [effectual-planning-agent]
tags: [workflow, decision-queue]
---

# Decision Queue: Batch Decision Processing for Task Unblocking

**Task**: `aops-f4b71ada`
**Status**: Requirements confirmed - ready for implementation
**Author**: Claude (Audre)
**Date**: 2026-02-03

## Giving Effect

- [[skills/decision-extract/SKILL.md]] - Skill for extracting pending decisions to daily note
- [[skills/decision-apply/SKILL.md]] - Skill for applying annotated decisions back to sources
- [[agents/effectual-planner.md]] - Agent that orchestrates decision queue workflow

## Problem Statement

Not all blocked tasks require substantive work. Many are waiting for a simple decision:

- RSVP to a meeting invitation (yes/no/maybe)
- Approve or reject an email draft
- Sign off on a code review
- Go/no-go on a proposal
- Choose between options A, B, or C

These decisions scatter across:

- Task system (tasks with `status: waiting` or `assignee: nic`)
- Outlook calendar (meeting invitations awaiting response)
- Outlook inbox (emails requiring a reply decision)
- Code review requests (PRs awaiting approval)

The cognitive load of context-switching between these scattered decisions creates friction. Worse, undecided items silently block downstream work - a single unreviewed PR can stall an entire feature branch.

## Proposed Solution

A two-phase workflow orchestrated by the effectual planner:

### Phase 1: Extract (`/decision-extract`)

The effectual planner scans all decision sources and produces a prioritized markdown section in the daily note containing:

1. Each pending decision with context
2. Space for the user's annotation
3. Priority ordering based on:
   - How many other tasks this decision unblocks
   - Due dates/deadlines
   - Age (older decisions surface first)

### Phase 2: Apply (`/decision-apply`)

After the user annotates their decisions, a second skill:

1. Reads the annotated daily note
2. Updates the original sources (tasks, etc.)
3. Unblocks dependent tasks
4. Reports what was resolved

## User Expectations

As a core part of the academicOps workflow, the Decision Queue must meet the following user expectations:

- **Visibility**: I expect to see a summary of pending decisions (count and high-priority highlights) in my morning briefing (`/daily`).
- **One-Stop Batching**: I expect to be able to trigger a full extraction (`/decision-extract`) that gathers all decision-type tasks from across the system into my daily note.
- **Decision-Ready Context**: I expect each entry in the queue to provide sufficient context—including the task title, a snippet of the task body, and the number of downstream tasks it is blocking—so I can make a decision without having to open the original task file.
- **Frictionless Annotation**: I expect to record my decisions using simple markdown interactions (checking boxes like `[x] Approve` or `[x] Defer`) and adding optional notes in the provided space.
- **Reliable Execution**: I expect that running `/decision-apply` will faithfully update the task system, change statuses as intended, and provide a clear report of which tasks were unblocked.
- **Safety First**: I expect the system to never perform irreversible external actions (such as sending an email or declining a calendar invite) without my explicit, separate confirmation or the use of a specialized communication skill.
- **Persistence**: I expect my annotations to be preserved if I refresh the decision queue or run the daily update multiple times.
- **Graceful Deferral**: I expect to be able to skip or defer some decisions without the system failing or losing track of the remaining items.

## Decision Classification

### What IS a Decision

| Source           | Decision Type                           | Example                             |
| ---------------- | --------------------------------------- | ----------------------------------- |
| Task system      | Status = `waiting` with `assignee: nic` | "Approve design doc"                |
| Task system      | Status = `review`                       | "Review implementation"             |
| Task system      | Type = `decision` (proposed new type)   | "Choose auth provider"              |
| Outlook calendar | Unresponded meeting invitation          | "Team standup - RSVP"               |
| Outlook inbox    | Flagged email awaiting reply            | "Vendor proposal - reply needed"    |
| Code review      | PR assigned for review                  | "PR #123 - approve/request changes" |

### What is NOT a Decision

| Item                           | Why Excluded                      |
| ------------------------------ | --------------------------------- |
| Task: "Write chapter 3"        | Requires substantive work         |
| Task: "Fix authentication bug" | Requires investigation and coding |
| Email: Newsletter              | No response expected              |
| Calendar: Accepted meeting     | Already decided                   |

### Decision Detection Heuristics

**From task system:**

```
(status = 'waiting' OR status = 'review')
AND assignee = 'nic'
AND type NOT IN ('project', 'epic', 'goal')
```

**From Outlook calendar:**

```
response_status = 'not_responded'
AND start_date > now()
```

**From Outlook inbox:**

```
is_flagged = true
OR category = 'Decision Required'
```

## Output Format: Decision Queue File

Location: `~/src/academicOps/data/decision-queue/YYYY-MM-DD-decisions.md`

````markdown
# Decision Queue - 2026-02-03

Generated by effectual planner at 14:30 UTC.

## Instructions

For each decision below:

1. Read the context
2. Write your decision in the `Decision:` field
3. Optionally add notes
4. Save the file

Then run `/decision-apply` to process your decisions.

---

## High Priority (Blocking Multiple Tasks)

### D001: Approve authentication provider choice

**Source**: Task `aops-abc123`
**Blocks**: 3 tasks (login-ui, session-mgmt, user-tests)
**Context**: Options are Auth0 vs Cognito. See [[auth-provider-comparison]]
**Due**: 2026-02-05

**Decision**: _________________
**Notes**:

---

### D002: RSVP - Architecture Review Meeting

**Source**: Outlook Calendar `entry_id_xyz`
**When**: 2026-02-04 10:00 - 11:00
**Organizer**: alice@example.com
**Context**: Reviewing API design for v2

**Decision**: [ ] Accept [ ] Decline [ ] Tentative
**Notes**:

---

## Medium Priority

### D003: Reply to vendor proposal

**Source**: Outlook Inbox `entry_id_abc`
**From**: vendor@example.com
**Subject**: Pricing proposal for Q2
**Received**: 2026-01-28 (5 days ago)
**Context**: (first 200 chars of email body)

**Decision**: [ ] Reply Yes [ ] Reply No [ ] Need more info [ ] Delegate
**Notes**:

---

## Low Priority (No Downstream Dependencies)

### D004: Review PR #456 - Fix typo in readme

**Source**: GitHub PR
**Author**: bob
**Age**: 2 days

**Decision**: [ ] Approve [ ] Request changes [ ] Skip
**Notes**:

---

## Summary

- **Total decisions**: 4
- **High priority**: 2
- **Medium priority**: 1
- **Low priority**: 1
- **Estimated time**: 15-20 minutes

---

<!-- Machine-readable section - DO NOT EDIT -->

```yaml
decisions:
  - id: D001
    source_type: task
    source_id: aops-abc123
    decision: null
    processed: false
  - id: D002
    source_type: calendar
    source_id: entry_id_xyz
    decision: null
    processed: false
  # ...
```
````

````
## Apply Phase Logic

When `/decision-apply` runs:

### For Task Decisions
```python
if decision in ['approve', 'yes', 'go']:
    update_task(id, status='active')  # Unblock
    # Also unblock all tasks that depend_on this one
elif decision in ['reject', 'no', 'cancel']:
    update_task(id, status='cancelled')
    # Handle orphaned dependents
````

### For Calendar RSVPs

```python
if decision == 'accept':
    calendar_accept_invitation(entry_id)
elif decision == 'decline':
    calendar_respond_to_meeting(entry_id, response='decline')
elif decision == 'tentative':
    calendar_respond_to_meeting(entry_id, response='tentative')
```

### For Email Replies

```python
if decision == 'reply_yes':
    if notes is None:
        raise ValueError("Notes required for email reply decision")
    messages_reply(entry_id, body=notes)
elif decision == 'delegate':
    if delegate_email is None:
        raise ValueError("Delegate email required for delegation")
    messages_forward(entry_id, to=delegate_email, body=notes)
```

## Integration Points

### With Daily Note (`/daily`)

The daily skill should include a "Pending Decisions" section:

```markdown
## Pending Decisions (5)

You have 5 decisions awaiting your input:

- 2 high priority (blocking other work)
- 3 low priority

Run `/decision-extract` to batch process them.
```

### With Effectual Planner Agent

The effectual planner can be invoked directly:

```
"What decisions am I blocking? Show me everything waiting on me."
```

This should invoke the decision extraction logic and present results conversationally.

## Implementation Phases

### Phase A: Core Task Integration (COMPLETED)

- [x] Task system integration (status: waiting/review, assignee: nic)
- [x] Output location: Daily note inline
- [x] Apply behavior: Automatic PKB updates (status, body log)
- [x] Frequency: Summary in `/daily`, full extraction via `/decision-extract`

### Phase B: Context & Prioritization (ACTIVE)

- [x] Priority ordering by blocking count (leverage graph topology)
- [x] Multi-tier classification (High/Medium/Low priority)
- [ ] Integration with `decision-briefing` workflow for complex choices

### Phase C: Expansion (BACKLOG)

- [ ] Outlook calendar integration (unresponded invitations)
- [ ] Outlook inbox integration (flagged/categorized emails)
- [ ] GitHub PR integration (assigned reviews)

### Phase D: Advanced Features (BACKLOG)

- [ ] Decision expiry/archiving logic
- [ ] Undo support for applied decisions (where possible)
- [ ] Delegation support (automatic subtask creation)

## Open Questions

1. **Partial decisions**: What if the user only annotates some decisions? Skip the rest? Prompt?

2. **Decision expiry**: Should old unannotated decision files be auto-archived?

3. **Undo**: If a decision was wrong, how to reverse? (Especially for sent emails)

4. **Conflict resolution**: What if the same item appears in multiple extracts?

5. **Delegation decisions**: Should "delegate to X" create a new task assigned to X?

## Success Criteria

1. User can run `/decision-extract` and get a prioritized list within 30 seconds
2. Annotating the file takes <1 minute per decision (just marking checkboxes)
3. Running `/decision-apply` unblocks dependent tasks automatically
4. Daily note surfaces decision count without running full extraction
5. Decision backlog trends downward over time (measurable)

## Related Work

- [[effectual-planner]] - Strategic planning under uncertainty
- [[work-management]] - Task system documentation
- [[daily]] - Daily briefing integration point
- [[collaborate-workflow]] - Human-agent collaboration patterns
