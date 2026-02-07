---
id: qa-test
category: quality-assurance
bases: []
audience: LLM agents conducting acceptance testing for any aops-managed project
description: End-to-end user acceptance testing workflow. Creates test plans as tasks, runs qualitative evaluations, and tracks failures as new tasks.
---

# User Acceptance Testing Workflow

This workflow governs end-to-end acceptance testing. It is distinct from unit/integration testing (which uses scripts). Acceptance tests verify that the system works **from the user's perspective**.

## Core Principles

### 1. Black-Box Testing Only

You are testing the system as a user would experience it. You do NOT:
- Read source code to understand expected behavior
- Examine implementation details
- Peek at logs or internal state

You DO:
- Provide inputs (prompts, commands)
- Observe outputs (responses, side effects)
- Compare outputs to acceptance criteria from specifications

**If you don't know what output to expect, the test plan is incomplete. Fix the plan, don't investigate the code.**

### 2. Qualitative Over Mechanical

Acceptance testing is NOT about running scripts and checking exit codes. The agent oversees the entire process, making judgment calls about quality.

For each test case, evaluate:
- Did the system understand the user's intent?
- Was the response helpful and appropriate?
- Was the interaction efficient or wasteful?
- Did error handling work gracefully?
- Would a real user be satisfied?

**Qualitative dimensions matter more than pass/fail counts.** A system that passes 4/5 tests but provides poor user experience has failed acceptance testing.

### 3. Acceptance Criteria Come From Specs

Find acceptance criteria in:
- Feature specifications
- User stories
- Design documents
- Issue/task descriptions

**NEVER derive acceptance criteria from code.** The code may be wrong. That's what you're testing.

### 4. Failures Are Not Excused

When a test fails:
- Document exactly what happened
- Create a new task to address the failure
- Do NOT mark the test as "partial pass" or "acceptable given constraints"
- Do NOT adjust criteria to make failures pass

A failure is a failure. Either the system needs fixing or the spec needs updating. Both require explicit action.

## Workflow Steps

### Step 1: Create Test Plan Task

Create a task of type `task` with:

```yaml
title: "QA Test Plan: [Feature Name]"
type: task
status: active
assignee: bot
complexity: requires-judgment
tags: [qa, acceptance-test]
```

The task body must include:
1. **Scope**: What feature/behavior is being tested
2. **Acceptance Criteria**: From the spec (with source reference)
3. **Test Cases**: Each with trigger, expected outcome, evaluation method
4. **Qualitative Rubric**: How to assess quality beyond pass/fail

### Step 2: Get Plan Approved

Before execution:
- Review the plan for completeness
- Verify all acceptance criteria are testable
- Confirm qualitative rubric is appropriate
- Get human approval (status → `in_progress`)

### Step 3: Execute Tests

For each test case:
1. Set up preconditions
2. Execute the trigger action
3. Capture all outputs (responses, transcripts, side effects)
4. Evaluate against expected outcomes
5. Score qualitative dimensions
6. Document evidence (quotes, screenshots, logs)

### Step 4: Report Results

Create a test report with:
- Summary table (test case → result)
- Qualitative scores with evidence
- Detailed findings for each test
- List of issues found

### Step 5: Handle Failures

For each failure:
1. Create a new task describing the issue
2. Link it to the test plan task
3. Set appropriate priority based on severity
4. Do NOT close the test plan until all failures are addressed or explicitly deferred

## Task Structure

```
[Epic] Acceptance Testing: [Feature]
├── [Task] QA Test Plan: [Feature] (design + approval)
├── [Task] Execute QA Tests: [Feature] (depends on plan)
├── [Task] Fix: [Issue 1] (created from test failure)
├── [Task] Fix: [Issue 2] (created from test failure)
└── [Task] Retest: [Feature] (after fixes)
```

## What This Workflow Is NOT

- **Unit testing**: Use automated test suites
- **Integration testing**: Use CI/CD pipelines
- **Code review**: Use peer review workflows
- **Performance testing**: Use benchmarking tools

This workflow is for answering: "Does the feature work correctly from a user's perspective?"

## Invocation

```
Task(subagent_type="qa",
     prompt="Execute acceptance test plan from task [TASK-ID].
             Evaluate qualitatively, document failures as new tasks.")
```
