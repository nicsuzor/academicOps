---
alias:
- wf-tdd-cycle-wf-tdd-cycle
- wf-tdd-cycle
- wf_tdd_5b47ec98
created: 2026-07-11T12:42:45.866926970+00:00
description: Red-green-refactor cycle for testable code changes. Composed into feature development and bug-fixing workflows. Not a standalone workflow.
id: wf-tdd
last_modified: 2026-09-02T00:00:00.000000000+00:00
modified: 2026-09-02T00:00:00.000000000+00:00
permalink: wf-tdd
tags:
- wf-template
- v0.4
- module-f
- prose-lens
title: wf-tdd
type: template
---

## What this step does

Red-green-refactor development for any testable code change. A domain-specialized instance of the generic build-then-verify loop, for the specific case where the artifact is code and correctness is machine-checkable.

## Procedure

1. **Red** — write a failing test for ONE behavior, asserting on its public API or observable I/O — never on internal state, a private method, or a mock's own call log. The expected value must be one the correct implementation has to derive, not a literal you are about to paste into that implementation.
   - Bad (tautological): `assert result == "42"`, then writing `return "42"`.
   - Good (behavioral): `assert result == expected_total(sample_order)`, where the expected value is computed independently of the code under test.
2. **Verify failure** — run the test and capture the failure trace before implementing. It must fail on the assertion — proof the behavior is genuinely absent — not on a syntax, import, or fixture error, which proves only that the test is broken. A test that passes immediately, or fails for the wrong reason, is not red: HALT and rewrite it.
3. **Green** — minimal implementation to pass. Not the most elegant implementation; just enough.
4. **Verify pass** — run the test and cite the passing output; a claimed pass with no run is not verified.
5. **Refactor** (optional) — cleanup while keeping tests green. Only allowed while tests are green; if refactoring breaks a test, undo the refactor rather than pushing forward on a broken base.
6. **Repeat** if acceptance criteria remain; otherwise proceed to commit.

## Constraints (normative)

- One behavior per test, one behavior per cycle.
- Test before code — never implement before a test exists for that behavior.
- Black-box only: assert what the unit does (inputs → output or observable effect), never how — no reaching into private state, internals, or a mock's invocation history to make the assertion trivially true.
- No tautologies: never assert against a hardcoded value inserted solely to satisfy that one assertion. If the assertion and the implementation could be derived from each other by copy-paste, the test proves nothing.
- Never commit with a failing test.
- Never commit a failing test without its implementation (an incomplete cycle is not a checkpoint).
- Never implement beyond the minimum needed to pass the current test.

## Output contract

The handback for a TDD-cycled change states: which behaviors were covered by which tests (a simple list is fine), the red failure trace captured for each as proof the test was genuine, confirmation that all tests in scope are green (not just the new one — full-suite pass, since refactor steps can regress siblings), and any refactor steps taken. If a cycle was abandoned or a test needed reworking mid-cycle, say so — an evidence-or-failure-reason discipline applies here exactly as in `wf-qa-verify`.

## When to include

- Any testable code change where correctness can be pinned down by an executable assertion.
- Not useful for prose/judgment artifacts, exploratory spikes (see `wf-decompose`), or UI/UX work where "correct" isn't a single assertion — use `wf-qa-verify`'s qualitative-assessment mode instead.
- Composes as the implementation phase inside a larger `wf-qa-verify`-gated feature: the TDD cycle produces the artifact; `wf-qa-verify` (or `wf-critique-lens` for framework-level changes) is the independent check that the artifact is actually right, not just internally test-consistent.

## Source material (provenance)

Reworked from the retired workflow template `base-tdd.md`, largely intact — no longer on the tree; git holds it. The original was already a clean, self-contained composable pattern with an explicit state machine and check predicates; this rework repackages it with an output contract and when-to-include guidance to match the wf-* seed bar. Part of epic_5e9fc3d5 (SSoT: note_296e5520 D4).
