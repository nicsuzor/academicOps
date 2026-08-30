---
id: tdd
type: template
kind: fragment
category: fragment
description: Red-green-refactor cycle for any testable code change
requires: []
pairs-with: [wf-verification]
conflicts: []
version: 1.0.0
permalink: workflows-process-tdd
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---
> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process fragment: Test-Driven Development

**Composable fragment.** Used by development-shaped process templates.

## Pattern

1. **Red**: write a failing test for ONE behavior.
2. **Verify failure**: confirm it fails (proves the test is meaningful). Valid
   red is an `AssertionError` on behavior — `TypeError` means the test is
   malformed, add a minimal stub first.
3. **Green**: minimal implementation to pass. Only build what the test requires.
4. **Verify pass**: confirm the test now passes.
5. **Refactor**: optional cleanup, tests must stay green.
6. **Repeat** if acceptance criteria remain.

## Rules

- A test must exist before implementation begins.
- Every test result must be explained: a pass before implementation is either
  a labelled `[GREEN]` regression guard, or the test is wrong — never call it
  "accidental" and move on.
- Never implement before writing a test; never commit with a failing test.

## Escalation

- Unexpected pass on red → HALT, the test doesn't test what you think.
- Fail after refactor → undo the refactor, don't debug forward from a broken
  known-good state.
