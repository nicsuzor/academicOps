---
description: "Worker: red-green test cycle for a code change, only in repositories that already keep a test suite."
id: wf-tdd
tags:
  - wf-template
  - tdd
title: Red-green tests
type: template
---

## What this step does

Adds a test that catches the bug or proves the behaviour, written before the fix. Include it only when the repository already keeps a test suite and the change is to code that executes. Never for docs, instruction text or config, and never in a repository without tests or whose instructions forbid them.

## Procedure

1. Write one test of the behaviour through its public interface, with expected values worked out independently of the code.
2. Run it and see it fail on the assertion (not on an import or syntax error).
3. Make the smallest change that turns it green, then run the repository's suite.

## Rules

- Assert outputs, never wording, private helpers, call order or mock call logs.
- Hermetic: no network, live services, clock or unseeded randomness.
- Never commit a failing test.

## Output contract

The test, its red-then-green output, and the suite result in the report.

## When to include

A code change in a repository with a test suite, where the task's class or ask calls for a regression test.
