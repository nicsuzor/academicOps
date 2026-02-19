---
title: Decision Queue Specification
status: draft
created: 2026-01-21
updated: 2026-01-21
---

# Decision Queue Specification

The Decision Queue provides a structured way for agents to escalate judgment calls to the human user and for the user to batch-process those decisions.

## 1. Core Model

A **decision** is a state transition for a task that requires human judgment.

### 1.1 Decision Sources

1. **Task system** (tasks with `status: waiting` or `assignee: human`)
2. **Review system** (tasks with `status: review`)
3. **Constraint system** (agent halted by hook needing authorization)

### 1.2 Decision Schema

```yaml
id: D-[hash8]
task_id: [task-id]
type: [approve_plan | confirm_step | select_option | authorize_tool]
context: [1-2 sentences explaining the decision]
options:
  - label: [text]
    action: [transition_to_status | resume_workflow]
status: [pending | resolved | deferred]
```

## 2. Extraction Logic

The `/decision-extract` skill identifies pending decisions:

### 2.1 Filtering

- `status = 'waiting'`
- `status = 'review'`
- AND assignee = 'human'

### 2.2 Prioritization

Decisions are prioritized by:

1. **Blocking count**: How many tasks depend on this? (Higher = more urgent)
2. **Priority**: The priority of the task itself (P0 > P1)
3. **Age**: Older decisions first

## 3. UI/UX (Daily Note)

The daily note includes a `## Pending Decisions` section.

| Source      | Status                                    | Task                 | Context                         |
| ----------- | ----------------------------------------- | -------------------- | ------------------------------- |
| Task system | Status = `waiting` with `assignee: human` | "Approve design doc" | Options: approve, reject, defer |

## 4. Resolution Flow

1. User annotates daily note: `[x] Approve`
2. User runs `/decision-apply`
3. Agent reads daily note, parses annotations
4. Agent updates task status and unblocks dependents

## 5. Verification

- [x] Task system (status: waiting/review, assignee: human)
- [ ] PR system (waiting for review)
- [ ] Memory system (conflicting information)
