---
title: Feature Development
type: template
category: process
description: Test-first development for a new feature or known-cause bug from requirement to ship. Select when adding capability or fixing a bug whose root cause is already established. Not for unknown-cause debugging (use `investigation`) or runtime-only repro loops (use `live-fix-loop`).
tags: [development, feature, bugfix, tdd, process]
---

# Process: Feature Development

End-to-end development cycle for implementing new functionality or fixing a defect with an established root cause.

## 1. Specification and Acceptance Criteria

- Define the target interface, input/output behavior, and constraints for `<target>`.
- State concrete, machine-verifiable acceptance criteria before modifying code.
- Identify applicable test suites and runtime environments (`<test-suite>`).

## 2. Test-First Implementation

- Compose `tdd` for each unit of functionality:
  - Write a failing test asserting the expected behavior of `<target>`.
  - Verify the test fails for the expected reason (e.g. assertion failure, not malformed test setup).
  - Implement minimal code to pass the test.
  - Verify the test passes.

## 3. Local Verification and Regression Guard

- Run the full test suite (`<verification-suite>`) to confirm no regressions.
- Execute linter and type-checker to ensure static integrity.
- Verify that edge cases and boundary conditions identified in step 1 are covered.

## 4. Documentation and Handover

- Update user-facing documentation, docstrings, or API schemas where interface changes occurred.
- Compose `wf-handover`: commit changes with structured message, create pull request, and summarize outcome.
