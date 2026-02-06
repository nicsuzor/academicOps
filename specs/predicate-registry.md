---
title: Predicate Registry
type: spec
category: architecture
status: draft
created: 2026-01-23
related: [workflow-constraints, prompt-hydrator]
---

# Predicate Registry

## Giving Effect

- [[workflows/constraint-check.md]] - Workflow that uses predicates for constraint verification
- [[agents/prompt-hydrator.md]] - Hydrator that checks constraints using predicates
- [[specs/workflow-constraints.md]] - Constraint specification referencing this registry
- [[specs/constraint-checking-tests.md]] - Test specification for predicate validation

Standard predicate definitions for workflow constraint checking. Used by the prompt-hydrator to verify execution plans satisfy workflow constraints.

## Purpose

Workflows define constraints using predicates like `tests_exist`, `plan_approved`, etc. This registry defines:
1. What each predicate means
2. How to verify it at planning time (static check)
3. How to verify it at execution time (runtime check)

## Predicate Categories

### Test Predicates

| Predicate | Meaning | Planning Check | Runtime Check |
|-----------|---------|----------------|---------------|
| `tests_exist` | Test files exist for the feature/bug | Plan has "Write test" or "Create test" step | grep finds `def test_` or `test(` in relevant test files |
| `tests_pass` | All relevant tests pass | Plan has "Run tests" step expecting success | pytest/test runner exit code == 0 |
| `tests_fail` | Tests fail (expected before implementation) | Plan expects tests to fail after writing | pytest/test runner exit code != 0 |
| `tests_still_pass` | Tests pass after change (no regression) | Plan has "Verify no regressions" step | Full test suite passes, not just new tests |
| `no_regressions` | No existing tests broken | Plan has regression check | Compare test results before/after |

### Approval Predicates

| Predicate | Meaning | Planning Check | Runtime Check |
|-----------|---------|----------------|---------------|
| `plan_approved` | Implementation plan has human approval | Plan references approved plan or has approval step | Task body contains "## Approved Plan" or user said "approved"/"lgtm" |
| `critic_reviewed` | Critic agent has reviewed | Plan includes `Task(subagent_type='critic', ...)` or `Task(subagent_type='qa', ...)` | Critic agent was spawned and returned verdict |
| `review_approved` | Human review task completed | Plan has "Await review approval" step | Review task status == "done" |
| `user_approved` | User explicitly approved action | N/A (runtime only) | User message matches approval pattern |

### Task State Predicates

| Predicate | Meaning | Planning Check | Runtime Check |
|-----------|---------|----------------|---------------|
| `task_claimed` | Task is bound to session | Plan has task update with status="active" | Task exists with status="active" |
| `one_task_in_progress` | Only one task active | Plan doesn't claim multiple tasks | MCP query shows exactly one active task |
| `task_exists` | Task exists in system | Plan references task ID | `get_task(id)` succeeds |
| `implementation_complete` | All implementation steps done | All implementation TodoWrite items present | All implementation todos marked completed |

### Content Predicates

| Predicate | Meaning | Planning Check | Runtime Check |
|-----------|---------|----------------|---------------|
| `user_story_captured` | User story documented | Plan has "Capture user story" step | Task body contains "## User Story" |
| `requirements_documented` | Requirements specified | Plan has "Document requirements" step | Task body contains "## Requirements" |
| `success_criteria_defined` | Acceptance criteria listed | Acceptance Criteria section in plan | Task body contains "## Success Criteria" |
| `experiment_plan_exists` | Experiment documented | Plan references experiment task | Task with tag "experiment" exists |

### File/Code Predicates

| Predicate | Meaning | Planning Check | Runtime Check |
|-----------|---------|----------------|---------------|
| `file_exists` | Specified file exists | N/A (runtime only) | Glob/Read succeeds |
| `file_modified` | File was changed | Plan has Edit/Write step for file | Git diff shows changes |
| `changes_committed` | Changes in git | Plan has commit step | Git status clean |
| `no_uncommitted_changes` | Working tree clean | N/A (runtime only) | Git status shows nothing to commit |

### Workflow State Predicates

| Predicate | Meaning | Planning Check | Runtime Check |
|-----------|---------|----------------|---------------|
| `modifying_framework` | Changes affect aops-core/ | Task involves framework files | Files touched include "aops-core/" |
| `modifying_python` | Changes affect .py files | Task involves Python code | Files touched have .py extension |
| `blocked_on_infrastructure` | External dependency blocking | N/A (runtime only) | Error indicates missing tool/service |
| `requirements_unclear` | Ambiguity in requirements | N/A (runtime only) | Clarifying question needed |

## Usage in Constraint Checking

### Planning Time (Hydrator)

The hydrator checks predicates by examining the proposed TodoWrite plan:

```
Constraint: BEFORE implement: tests_exist AND tests_fail

Planning Check:
1. Find "implement" step in TodoWrite
2. Find "write test" step
3. Verify "write test" comes before "implement"
4. Verify plan expects tests to fail (not pass) after writing
```

### Runtime (Executor)

The executor verifies predicates during execution:

```
Constraint: BEFORE commit: tests_pass

Runtime Check:
1. Before commit step, run pytest
2. Verify exit code == 0
3. If fails, halt (don't proceed to commit)
```

## Predicate Composition

Predicates can be combined with AND/OR:

| Composite | Meaning |
|-----------|---------|
| `tests_exist AND tests_fail` | Tests written AND they fail (TDD red phase) |
| `tests_pass AND critic_reviewed` | Tests green AND critic approved |
| `plan_approved OR user_approved` | Either formal plan approval OR inline approval |

## Heuristic Predicates

Some predicates require human judgment and cannot be automatically verified:

| Predicate | Why Heuristic | How to Handle |
|-----------|---------------|---------------|
| `minimal_implementation` | Subjective - "just enough to pass" | Flag for review, don't auto-fail |
| `single_behavior_per_test` | Judgment call on test scope | Provide guidance, not enforcement |
| `good_commit_message` | Style/quality judgment | Critic can review, not block |

For heuristic predicates, the hydrator should:
1. Include the check in the plan as a recommendation
2. Note it as "requires human review" if violated
3. Not block the plan automatically

## Adding New Predicates

When adding a predicate to a workflow:

1. **Define it here** with meaning, planning check, and runtime check
2. **Categorize it** (test, approval, task state, content, file/code, workflow state, or heuristic)
3. **Specify composition rules** if it combines with other predicates
4. **Update the hydrator** if new check logic is needed

## Related Documents

- [[workflow-constraints]] - Constraint specification format
- [[prompt-hydrator]] - Agent that performs constraint checking
- [[enforcement]] - Runtime enforcement layer
