---
description: Testing standards and red-green-refactor cycle for testable code changes.
id: wf-tdd
tags:
  - wf-template
  - tdd
title: wf-tdd
type: template
---

## What this step does

Red-green-refactor development for any testable code change, where correctness is machine-checkable.

## Procedure

1. **Red** -- write a failing test for ONE behavior, asserting on its public API or observable I/O -- never on internal state or a mock's call log. The expected value must be one the implementation has to derive, not a literal about to be pasted into it.
2. **Verify failure** -- run the test and capture the failure trace before implementing. It must fail on the assertion, not on a syntax, import, or fixture error. A test that passes immediately, or fails for the wrong reason, is not red: halt and rewrite it.
3. **Green** -- minimal implementation to pass, nothing more.
4. **Verify pass** -- run the test and cite the passing output; a claimed pass with no run is not verified.
5. **Refactor** (optional) -- only while tests stay green; if it breaks a test, undo the refactor rather than pushing forward on a broken base.
6. **Repeat** if acceptance criteria remain; otherwise commit.

## Constraints (normative)

- One behavior per test, one behavior per cycle. Test before code.
- Black-box only: assert inputs → output or observable effect, never internals.
- No tautologies -- never assert against a hardcoded value inserted solely to satisfy that assertion.
- No configuration mirrors -- never assert that an agent, skill, settings, or instruction file _contains_ a given string, tool name, or skill name. Test what the code does with the file (it parses, a path it names resolves, its content drives an observable effect), never that the file says what was just written into it. A test of the form "`sara.md` contains tool x" fails on every legitimate edit to `sara.md` and proves nothing about behavior. If a value must be checked, read it live from its real source and compare it to a real, independently-produced outcome -- never restate the value as a second literal in the test.
- At least 2-3 distinct cases per non-trivial behavior, including boundary and error conditions.
- Never commit with a failing test, or a failing test without its implementation.
- Never implement beyond the minimum needed to pass the current test.

## Output contract

State which behaviors were covered by which tests, the red failure trace for each as proof the test was genuine, confirmation the full suite is green (not just the new test -- refactor steps can regress siblings), and any refactor steps taken. If a cycle was abandoned or reworked mid-cycle, say so.

## When to include

Any testable code change with machine-checkable correctness. Composes as the implementation phase inside a larger [[wf-qa]]-gated feature: the TDD cycle produces the artifact; [[wf-qa]] independently checks it's actually right.
