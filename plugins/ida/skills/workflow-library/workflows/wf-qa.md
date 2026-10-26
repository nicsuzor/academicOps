---
alias:
  - wf-qa
  - wf-quality-review
description: Universal quality and requirement-satisfaction review gate -- test the artifact against available specifications, requirements, and acceptance criteria (treating their absence as a critical failure signal), execute live test suites and probes, and audit empirical evidence, returning a PASS, REVISE, or FAIL verdict.
id: wf-qa
tags:
  - wf-template
  - review
  - qa
  - verification
  - requirements
  - gate
title: Quality and Requirement-Satisfaction Review
type: template
---

## What this step does

Universal quality and requirement-satisfaction review gate (`marsha`): evaluates substantive quality, empirical runtime behavior ("running things"), and satisfaction of stated requirements against whatever specifications, requirements, or acceptance criteria are available. Assumes deliverables are broken until proven working through direct execution, live probes, and inspection of primary sources -- and treats the absence of any specifications, requirements, or acceptance criteria as an immediate critical failure signal (`FAIL` / `REJECT`).

## Input contract

Draws its brief from the shared review briefing. Additional role-specific inputs:

- **Specifications, requirements & acceptance criteria** -- explicit specifications, requirements, or acceptance criteria governing the artifact (from the task record, linked specification, or commissioning ask).
- **Test surface** -- test commands, test suites, or execution harnesses (for executable artifacts).

## Procedure

1. **Gate 0: Specification existence, core premise, and proportion** -- assemble whatever specifications, requirements, or acceptance criteria are available for the artifact and record them verbatim:
   - **Missing-criteria failure signal**: If **no specifications, requirements, or acceptance criteria are available**, halt immediately and issue `FAIL` (`REJECT` in composite reconciliation). The absence of testable specifications or criteria is itself a critical failure signal; never invent ad-hoc criteria on the author's behalf or pass an unspec'd artifact on intuition.
   - **Premise and proportion**: Evaluate the core premise and overall proportion first. If the premise is invalid or the change is fundamentally disproportionate, halt immediately and issue `FAIL` before executing exhaustive test suites or line-by-line repo auditing. Preserve full requirement and acceptance-criteria coverage when Gate 0 passes.
2. **Verify satisfaction of stated requirements and substantive quality** -- test the deliverable systematically against every available specification, requirement, and acceptance criterion, judging restatements by fidelity to meaning, completeness, and lack of distortion or overreach rather than verbatim wording. Evaluate substantive quality against the `excellence` baseline.
3. **Execute test suites** -- run test commands (`uv run pytest`, `npm test`, etc.) directly on the branch. Inspect raw stdout/stderr; every test must pass cleanly without unhandled errors. An evaluator that changes code or pushes fixes must not approve, accept, or merge its own changes; evaluators never file fix tasks or follow-up tasks.
4. **Red-to-green regression verification** -- where fixes are claimed, run regression tests against the base commit (to verify failure) and against the branch commit (to verify resolution).
5. **Live probes and runtime observation** -- run scratch probes and test scripts with real inputs and edge cases (e.g. empty diffs, varied input parameters, error conditions) to observe live execution behavior, exit codes, and output formats.
6. **Audit empirical claims and per-claim fail-fast** -- verify empirical claims in task reports and PR descriptions against primary source records (git history, CI logs, file contents). Locate touchpoints via `grep_search` and read complete relevant functions or sections via `view_file` without arbitrary line-count caps or env-var allowlist shortcuts. Apply per-claim fail-fast: record `UNMET` immediately once a cited claim is falsified without searching the codebase to author a fix.
7. **Review boundaries** -- operates strictly on quality, satisfaction of stated requirements, runtime execution, and empirical verification. Does not evaluate code against constitutional axioms or author mechanisms analysis (the compliance role, `rbg`) and does not evaluate PKB strategic direction or graph congruence (the strategic congruence role, `pauli`).
8. **Report and issue verdict**: return an itemized per-requirement / per-criterion status (`MET` / `UNMET` with pinpoint evidence) and exactly one verdict token: `PASS`, `REVISE`, or `FAIL`.

## Verdict contract

- **PASS**: Specifications/criteria exist, execution succeeds, all tests pass, and all stated requirements and acceptance criteria are empirically verified at a substantive excellence standard.
- **REVISE**: Governing specifications/criteria exist and the approach functions, but requires specific fixes for unmet requirements, edge cases, missing test coverage, or unverified claims.
- **FAIL**: No specifications, requirements, or acceptance criteria are available; or the artifact fails runtime execution, fails test suites, misses stated requirements, or contradicts empirical evidence.

## Output contract

The structured QA handback containing the per-requirement / per-criterion verification table with pinpoint evidence citations, test run outputs, and exactly one verdict token (`PASS`, `REVISE`, or `FAIL`). Every requirement and criterion must be accounted for, none silently dropped. A report missing evidence for a `MET` criterion is not a pass. If no specifications/criteria exist, or if any criterion is `UNMET` or the check fails, release the QA task as `failed` with failure evidence and root cause documented on the record; do not file fix tasks or follow-up tasks (the reconcile pass notes failed tasks and decides next actions from the parent epic). When all criteria are `MET`, release as `done` (or merge autonomously for verified Tier 1 PRs).

## When to include

Any workflow that produces a deliverable, specification, code change, or empirical report requiring verification against stated requirements and primary evidence before acceptance or merge.
