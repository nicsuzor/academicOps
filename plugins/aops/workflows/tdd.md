---
title: Test-Driven Development (TDD)
type: template
category: fragment
description: Red-green-refactor cycle for testable code changes. Composed into feature development and bug-fixing workflows. Not a standalone workflow.
tags: [tdd, testing, red-green, unit-tests, fragment]
---

# Fragment: Test-Driven Development

Standard red-green-refactor cycle for code modifications.

## 1. Red (Write Failing Test)

- Write an isolated, deterministic test asserting single expected behavior on `<target>`.
- Run test suite and confirm test fails with expected assertion error (not configuration/syntax error).

## 2. Green (Minimal Implementation)

- Implement the minimal code change necessary to satisfy the failing test.
- Do not add speculative functionality beyond what the test requires.
- Run test suite and confirm test now passes.

## 3. Refactor

- Clean up implementation for readability, maintainability, and efficiency.
- Re-run test suite to ensure tests remain green.

## 4. Repeat

- Repeat cycle for subsequent acceptance criteria until all behaviors are implemented.
