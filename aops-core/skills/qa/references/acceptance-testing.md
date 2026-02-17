# Acceptance Testing Mode

Full user acceptance testing workflow. Creates test plans, runs qualitative evaluations, tracks failures.

## When to Use

- End-to-end testing needed
- User perspective verification
- Quality beyond pass/fail

## Core Principles

1. **Black-box testing only**: Test as user would. Don't read source code.
2. **Qualitative over mechanical**: Judgment calls about quality, not just exit codes.
3. **Criteria from specs**: Never derive criteria from code.
4. **Failures are not excused**: Create task for each failure.

## Task Structure

```
[Epic] Acceptance Testing: [Feature]
├── [Task] QA Test Plan: [Feature]
├── [Task] Execute QA Tests: [Feature]
├── [Task] Fix: [Issue 1]
└── [Task] Retest: [Feature]
```

## Workflow Steps

1. Create test plan task with scope, acceptance criteria, test cases, qualitative rubric
2. Get plan approved (human reviews)
3. Execute tests: setup → trigger → capture → evaluate → score → document
4. Report results: summary table, qualitative scores, detailed findings
5. Handle failures: create task per failure, link to test plan

## Invocation

```
Task(subagent_type="qa",
     prompt="Execute acceptance test plan from task [TASK-ID]. Evaluate qualitatively, document failures as new tasks.")
```
