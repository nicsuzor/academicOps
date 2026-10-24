---
alias:
  - wf-qa
  - wf-quality-review
description: Universal QA review gate -- execute live test suites, verify red-to-green regression traces, run probes, and audit empirical evidence against acceptance criteria, returning a PASS, REVISE, or FAIL verdict.
id: wf-qa
tags:
  - wf-template
  - review
  - qa
  - verification
  - gate
title: Quality Assurance Review
type: template
---

## What this step does

Universal QA review gate: empirical runtime verification ("running things"). Assumes deliverables are broken until proven working through direct execution, live probes, and inspection of primary sources.

## Input contract

Draws its brief from the shared review briefing in `wf-review`. Additional role-specific inputs:

- **Test surface** -- test commands, test suites, or execution harnesses.

## Procedure

1. **Assemble criteria** -- record acceptance criteria verbatim from the specification before inspecting outputs.
2. **Execute test suites** -- run test commands (`pytest`, `npm test`, etc.) directly on the branch. Inspect raw stdout/stderr; every test must pass cleanly without unhandled errors. An evaluator that changes code or pushes fixes must not approve, accept, or merge its own changes; evaluators never file fix tasks or follow-up tasks.
3. **Red-to-green regression verification** -- where fixes are claimed, run regression tests against the base commit (to verify failure) and against the branch commit (to verify resolution).
4. **Live probes and runtime observation** -- run scratch probes and test scripts with real inputs and edge cases (e.g. empty diffs, varied input parameters, error conditions) to observe live execution behavior, exit codes, and output formats.
5. **Audit empirical claims** -- verify empirical claims in task reports and PR descriptions against primary source records (git history, CI logs, file contents). Falsify claims using direct command execution (e.g. running `git log`, `grep`).
6. **Review boundaries** -- operates strictly on runtime execution and empirical verification. Does not evaluate code against axioms or author mechanisms analysis (the rule-compliance role) and does not evaluate high-level PKB objective alignment (the strategic fit role).
7. **Report and issue verdict**: return an itemized per-criterion status (`MET` / `UNMET` with pinpoint evidence) and exactly one verdict token: `PASS`, `REVISE`, or `FAIL`.

## Verdict contract

- **PASS**: Execution succeeds, all tests pass, and all acceptance criteria are empirically verified with primary evidence.
- **REVISE**: Functioning approach, but requires specific fixes for edge cases, missing test coverage, or unverified claims.
- **FAIL**: Fails runtime execution, test suite fails, or empirical evidence contradicts claims.

## Output contract

The structured QA handback containing the per-criterion verification table with pinpoint evidence citations, test run outputs, and exactly one verdict token (`PASS`, `REVISE`, or `FAIL`). Every criterion must be accounted for, none silently dropped. A report missing evidence for a `MET` criterion is not a pass. If any criterion is `UNMET` or the check fails, release the QA task as `failed` with failure evidence and root cause documented on the record; do not file fix tasks or follow-up tasks (the reconcile pass notes failed tasks and decides next actions from the parent epic). When all criteria are `MET`, release as `done` (or merge autonomously for verified Tier 1 PRs).

## When to include

Any workflow that produces an executable deliverable, code change, or empirical report requiring runtime proof before acceptance or merge.
