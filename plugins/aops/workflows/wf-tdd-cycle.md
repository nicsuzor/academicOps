---
alias:
- wf-tdd-cycle-wf-tdd-cycle
- wf-tdd-cycle
created: 2026-07-11T12:42:45.866926970+00:00
id: wf_tdd_5b47ec98
last_modified: 2026-07-28T03:01:21.924973911+00:00
modified: 2026-07-28T03:01:21.924972208+00:00
permalink: wf-tdd-cycle
tags:
- wf-template
- v0.4
- module-f
- prose-lens
title: wf-tdd-cycle
type: template
---

## What this step does

Red-green-refactor development for any testable code change. A domain-specialized instance of the generic build-then-verify loop, for the specific case where the artifact is code and correctness is machine-checkable.

## Procedure

1. **Red** — write a failing test for ONE behavior. The test must exist before implementation begins.
2. **Verify failure** — confirm the test fails before you implement. This proves the test is actually testing something (a test that "passes" before implementation exists is testing nothing — HALT and reconsider the test if this happens).
3. **Green** — minimal implementation to pass. Not the most elegant implementation; just enough.
4. **Verify pass** — confirm the test passes.
5. **Refactor** (optional) — cleanup while keeping tests green. Only allowed while tests are green; if refactoring breaks a test, undo the refactor rather than pushing forward on a broken base.
6. **Repeat** if acceptance criteria remain; otherwise proceed to commit.

## Constraints (normative)

- One behavior per test, one behavior per cycle.
- Test before code — never implement before a test exists for that behavior.
- Never commit with a failing test.
- Never commit a failing test without its implementation (an incomplete cycle is not a checkpoint).
- Never implement beyond the minimum needed to pass the current test.

## Output contract

The handback for a TDD-cycled change states: which behaviors were covered by which tests (a simple list is fine), confirmation that all tests in scope are green (not just the new one — full-suite pass, since refactor steps can regress siblings), and any refactor steps taken. If a cycle was abandoned or a test needed reworking mid-cycle, say so — an evidence-or-failure-reason discipline applies here exactly as in `wf-qa-verify`.

## When to include

- Any testable code change where correctness can be pinned down by an executable assertion.
- Not useful for prose/judgment artifacts, exploratory spikes (see `wf-decompose`), or UI/UX work where "correct" isn't a single assertion — use `wf-qa-verify`'s qualitative-assessment mode instead.
- Composes as the implementation phase inside a larger `wf-qa-verify`-gated feature: the TDD cycle produces the artifact; `wf-qa-verify` (or `wf-critique-lens` for framework-level changes) is the independent check that the artifact is actually right, not just internally test-consistent.

## Source material (provenance)

Reworked from `archived/workflows/base-tdd.md`, largely intact — the original was already a clean, self-contained composable pattern with an explicit state machine and check predicates; this rework repackages it with an output contract and when-to-include guidance to match the wf-* seed bar. Part of epic_5e9fc3d5 (SSoT: note_296e5520 D4).
