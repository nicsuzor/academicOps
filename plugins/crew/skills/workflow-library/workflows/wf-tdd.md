---
description: Testing standards and red-green-refactor cycle for changes to code that executes.
id: wf-tdd
tags:
  - wf-template
  - tdd
title: Red-green-refactor TDD
type: template
---

## What this step does

Red-green-refactor development for changes to code that executes, where correctness is machine-checkable.

## Procedure

1. **Name the defect**: State the behavior added or fixed and the plausible bug the test will catch. If no executable code changes or no plausible bug exists, write no test; record a run or check as acceptance evidence instead.
2. **Red**: Write one failing test for one behavior asserting on its public API or observable I/O (never internal state or mock call logs), with expected values derived independently of the implementation.
3. **Verify failure**: Run the test before changing code and capture the failure trace; it must fail on the assertion rather than syntax, import, or fixture errors. Rewrite or drop any test that passes or fails for the wrong reason.
4. **Green**: Implement the minimal code needed to pass, nothing more.
5. **Verify pass**: Run the test and cite passing output.
6. **Refactor (optional)**: Refactor only while tests remain green; revert immediately if a test breaks.
7. **Repeat** until all acceptance criteria are covered, then commit with full suite green.

## Constraints (normative)

- **Outputs, never contents**: Assert observable outputs through the public interface (black-box), never phrasing, variable/enum names, private helpers, call order, or mock call logs. Write no unit tests for docs, instruction text (proved by an agent run), or configuration values (proved by applied live state).
- **One behavior per test/cycle, test before code**: Include at least 2--3 distinct cases per non-trivial behavior (including boundary and error conditions); bugfixes must reproduce the reported failure red-before-fix.
- **Mutation check, no tautologies, no mirror tests**: Introducing the named bug must turn the test red. Never assert against code-under-test outputs, tautological library primitives, or file/config/skill inventories; read any checked source live against an independent outcome.
- **Acceptance evidence vs. suite**: One-off verification outputs belong in the PR and task report, joining the test suite only when guarding executable code against regression.
- **Hermetic and deterministic**: No network, live services, wall clock, sleeps, unseeded randomness, or shared state; use temp directories and place test doubles strictly at process boundaries. Arrange-act-assert with descriptive failure messages. Never commit failing tests.

## Output Contract

State which behaviors each test covers, the defect caught, each red failure trace, confirmation the full suite is green, and any refactorings (or why no test was written if no executable behavior changed).

## When to Include

Any change to code that executes with machine-checkable correctness (never for docs, specs, or instruction text alone).
