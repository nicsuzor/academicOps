# Hydrator Test: GitHub Cold Start

This test evaluates hydrator performance when an agent picks up work from GitHub with no prior session context.

## Scenario

An agent is invoked with only:

- A GitHub issue reference
- No conversation history
- No prior knowledge of local task system state

## Test Prompt

```
Pick up GitHub issue nicsuzor/academicOps#394 and continue the work.
```

## Expected Hydrator Output

The hydrator SHOULD:

### 1. Fetch GitHub Context

- Issue body (current plan, audit tables)
- Issue comments (critic feedback, status signals)
- Issue metadata (labels, assignees, state)

### 2. Discover Local Task Binding

- Search task system for issue reference
- Find: `aops-84c88881` links to this issue
- Get task body with session notes

### 3. Identify Workflow

Route to `[[github-issue-cycle]]` workflow based on:

- GitHub issue coordination pattern
- Previous session notes mentioning this workflow
- Issue comment conventions (`[PLAN VERIFIED]`, etc.)

### 4. Compose Execution Steps

From `github-issue-cycle` + `base-task-tracking` + `base-tdd`:

1. Claim task `aops-84c88881` (or verify already claimed)
2. Fetch current state from GitHub issue
3. Check comments for status signals
4. Identify next step from decomposition plan
5. Execute one step (Step 1: Fix custom_actions.py)
6. Update GitHub with progress
7. Update local task
8. Handover

### 5. Provide Implementation Context

- Files to read: `aops-core/lib/gates/custom_actions.py`, `aops-core/lib/gate_model.py`
- Test files affected: listed in issue audit
- Acceptance criteria from issue body

## What Hydrator Currently Provides

(To be filled after test)

## Gap Analysis

| Expected                | Provided | Gap |
| ----------------------- | -------- | --- |
| GitHub issue fetch      | ?        | ?   |
| Local task discovery    | ?        | ?   |
| Workflow identification | ?        | ?   |
| Composed steps          | ?        | ?   |
| Implementation context  | ?        | ?   |

## Recommendations

(To be filled after test)
