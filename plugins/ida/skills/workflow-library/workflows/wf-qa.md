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

The invoking workflow provides:

1. **Target artifact** -- the file, diff, PR branch, or implementation under review.
2. **Acceptance criteria** -- explicit requirements and evidence obligations from the commission.
3. **Test surface** -- test commands, test suites, or execution harnesses.

## Procedure

1. **Assemble criteria** -- record acceptance criteria verbatim from the specification before inspecting outputs.
2. **Execute test suites** -- run test commands (`pytest`, `npm test`, etc.) directly on the branch. Inspect raw stdout/stderr; every test must pass cleanly without unhandled errors.
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

The structured QA handback containing the per-criterion verification table with pinpoint evidence citations, test run outputs, and exactly one verdict token (`PASS`, `REVISE`, or `FAIL`).

## When to include

Any workflow that produces an executable deliverable, code change, or empirical report requiring runtime proof before acceptance or merge.
