---
category: process
description: Testing standards and red-green-refactor cycle for testable code changes.
id: wf-tdd
tags:
  - wf-template
  - tdd
title: wf-tdd
type: template
---

## What this step does

Enforces red-green-refactor cycles for machine-checkable code changes.

## Procedure

1. **Red**: Write a failing test for a single behavior asserting on public interfaces and observable inputs/outputs.
2. **Verify failure**: Execute the test and capture the failure trace. The test must fail on the assertion itself, not on syntax or environment errors.
3. **Green**: Write the minimal implementation required to satisfy the test.
4. **Verify pass**: Run the test suite and confirm passing status.
5. **Refactor**: Improve design while ensuring the full test suite remains green.

## Testing Standards

- **Behavioral assertions**: Test public interfaces and side effects; avoid asserting on internal state or mock histories.
- **Non-tautological**: Do not assert against hardcoded constants duplicated directly from the implementation.
- **Edge cases and errors**: Cover boundary conditions, empty inputs, and expected exceptions.
- Commit code only with passing tests; never commit failing tests or untested implementations.

## Output Contract

Handback must report:

- Behaviors covered and corresponding test identifiers.
- Captured red failure trace demonstrating genuine pre-implementation failure.
- Full test suite execution log verifying all tests pass.
