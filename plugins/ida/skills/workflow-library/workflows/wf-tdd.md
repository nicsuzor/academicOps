---
description: Testing standards and red-green-refactor cycle for changes to code that executes.
id: wf-tdd
tags:
  - wf-template
  - tdd
title: wf-tdd
type: template
---

## What this step does

Red-green-refactor development for a change to code that executes, where correctness is machine-checkable.

## Procedure

1. **Name the defect** -- state the behaviour the change adds or fixes, and the plausible bug in that logic the test will catch. If the change touches no code that executes, or no plausible bug can be named, write no test: the acceptance evidence is a run or check reported on the task.
2. **Red** -- write a failing test for ONE behavior, asserting on its public API or observable I/O -- never on internal state or a mock's call log. The expected value must be derived independently of the implementation (a worked example, a known-good fixture), not a literal about to be pasted into it or copied from its output.
3. **Verify failure** -- run the test against the code before the change and capture the failure trace. It must fail on the assertion, not on a syntax, import, or fixture error. A test that passes immediately, or fails for the wrong reason, is not red: halt and rewrite it or drop it.
4. **Green** -- minimal implementation to pass, nothing more.
5. **Verify pass** -- run the test and cite the passing output; a claimed pass with no run is not verified.
6. **Refactor** (optional) -- only while tests stay green; if it breaks a test, undo the refactor rather than pushing forward on a broken base.
7. **Repeat** if acceptance criteria remain; otherwise commit.

## Constraints (normative)

- Tests check outputs, never contents. Never write unit tests for documentation or instruction files: text documents are not functions and produce no outputs, so we do not test them. For code, never write a test that asserts that code says a particular phrase or uses a particular variable, enum, constant, condition, or similar; assert observable outputs, never contents themselves.
- One behavior per test, one behavior per cycle. Test before code.
- Black-box only: assert inputs → output or observable effect through the public interface, never private helpers, internal state, call order, or a mock's call log.
- Mutation check: introducing the named bug must turn the test red. A test that survives it guards nothing; drop it.
- No tautologies -- never assert against a value the code under test produced, a literal inserted solely to satisfy the assertion, or a property that fails only if a library or language primitive (a copy, a glob, a parse) breaks.
- No change-detector (mirror) tests -- never assert that an agent, skill, settings, config, or instruction file, a mapping, or a directory holds what it holds today: a string, tool name, or skill name it contains, an entry the same change added, a source-to-dist file inventory. Test what the code does with the file (it parses, a path it names resolves, its content drives an observable effect). If a value must be checked, read it live from its real source and compare it to a real, independently-produced outcome -- never restate the value as a second literal in the test.
- Acceptance evidence is not a test: a one-off check that the change worked (a listing diff, a command's output, a fresh agent's run) goes in the PR and task report, and joins the suite only if it also guards code that executes against a plausible regression.
- A change to instruction text alone owes no test: a run that follows the instruction proves it.
- Hermetic and deterministic: no network, live services, wall clock, sleeps, unseeded randomness, or state shared between tests; use temp directories and fixtures. Test doubles only at process boundaries (network, model calls, clock), never on the unit under test.
- Arrange-act-assert, named for the behaviour and its condition, with a failure message that says what broke.
- At least 2-3 distinct cases per non-trivial behavior, including boundary and error conditions.
- A bug fix's test reproduces the reported failure, red before the fix.
- Never commit with a failing test, or a failing test without its implementation.
- Never implement beyond the minimum needed to pass the current test.

## Output contract

State which behaviors were covered by which tests and the defect each catches, the red failure trace for each as proof the test was genuine, confirmation the full suite is green (not just the new test -- refactor steps can regress siblings), and any refactor steps taken. If a cycle was abandoned or reworked mid-cycle, or no test was written because no executable behaviour changed, say so.

## When to include

Any change to code that executes with machine-checkable correctness. Not for a change to instruction text, docs or specs alone, and not for verifying a criterion that holds without a change to executable code.
