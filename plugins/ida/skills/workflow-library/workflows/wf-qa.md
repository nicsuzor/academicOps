---
alias:
  - wf-qa
  - wf-quality-review
description: Universal quality and requirement-satisfaction review -- test whether the artifact achieves ambitious quality across actual rendered multimodal outputs (never code alone or simulated renders), live test suites, and primary evidence against available specifications, requirements, and acceptance criteria (treating their absence as an immediate FAIL), returning a PASS, REVISE, or FAIL verdict.
id: wf-qa
tags:
  - wf-template
  - review
  - qa
  - verification
  - requirements
title: Quality and Requirement-Satisfaction Review
type: template
---

## What this step does

Universal quality and requirement-satisfaction review (`marsha`): evaluates whether the artifact, as presented, is amazingly good -- not merely working -- across actual rendered multimodal outputs, empirical runtime behavior ("running things"), and satisfaction of stated requirements against whatever specifications, requirements, or acceptance criteria are available. Assumes deliverables are broken until proven working through direct execution, live probes, rendered output inspection, and primary sources -- and treats the absence of any specifications, requirements, or acceptance criteria as an immediate critical failure signal (`FAIL`).

## Input contract

Draws its brief from the shared review briefing. Additional role-specific inputs:

- **Specifications, requirements & acceptance criteria** -- explicit specifications, requirements, or acceptance criteria governing the artifact (from the task record, linked specification, or commissioning ask).
- **Test and render surface** -- test commands, test suites, execution harnesses, and rendered output artifacts.

## Procedure

1. **Upfront specification check** -- assemble whatever specifications, requirements, or acceptance criteria are available for the artifact and record them verbatim:
   - **Missing-criteria failure signal**: If **no specifications, requirements, or acceptance criteria are available**, stop immediately and issue `FAIL`. The absence of testable specifications or criteria is itself a critical failure signal; never invent ad-hoc criteria on the author's behalf or pass an unspec'd artifact on intuition.
2. **Verify ambitious quality and satisfaction of stated requirements** -- when specifications, requirements, or acceptance criteria exist, test the deliverable systematically against every stated requirement and criterion with full coverage. Judge restatements by fidelity to meaning, completeness, and lack of distortion or overreach rather than verbatim wording. Demand ambitious, best-in-class quality (`excellence`) rather than mere checklist completion or mediocrity.
3. **Inspect actual rendered multimodal outputs (never code alone or simulations)** -- reading source code or diffs is never sufficient. Evaluate every artifact in its actual rendered, multimodal form (live execution output, rendered PDFs, visual plots, UI screenshots, built containers). Output renders may **never** be simulated, mocked, or inferred from source text.
4. **Execute test suites** -- run test commands (`uv run pytest`, `npm test`, etc.) directly on the branch. Inspect raw stdout/stderr; every test must pass cleanly without unhandled errors. An evaluator that changes code or pushes fixes must not approve, accept, or merge its own changes; evaluators never file fix tasks or follow-up tasks.
5. **Red-to-green regression verification** -- where fixes are claimed, run regression tests against the base commit (to verify failure) and against the branch commit (to verify resolution).
6. **Live probes and primary evidence audit** -- run scratch probes and test scripts with real inputs and edge cases (e.g. empty diffs, varied input parameters, error conditions) to observe live execution behavior, exit codes, and output formats. Verify empirical claims in task reports and PR descriptions against primary source records (git history, CI logs, raw data, file contents). Locate touchpoints via `grep_search` and read complete relevant functions or sections via `view_file` without arbitrary line-count caps or env-var allowlist shortcuts. Apply per-claim fail-fast: record `UNMET` immediately once a cited claim is falsified without searching the codebase to author a fix.
7. **Review boundaries** -- operates strictly on ambitious quality, satisfaction of stated requirements, rendered multimodal output verification, runtime execution, and empirical verification. Does not evaluate the strategic core premise or PKB graph congruence (the strategic congruence role, `pauli`) and does not evaluate code against constitutional axioms or author mechanisms analysis (the compliance role, `rbg`).
8. **Report and issue verdict**: return an itemized per-requirement / per-criterion status (`MET` / `UNMET` with pinpoint evidence) and exactly one verdict token: `PASS`, `REVISE`, or `FAIL`.

## Verdict contract

- **PASS**: Specifications/criteria exist, execution succeeds, actual rendered multimodal outputs are verified, all tests pass, and all stated requirements and acceptance criteria are empirically satisfied to an ambitious quality standard.
- **REVISE**: Governing specifications/criteria exist and the approach functions, but requires specific fixes for unmet requirements, edge cases, missing test coverage, quality polish, or unverified claims.
- **FAIL**: No specifications, requirements, or acceptance criteria are available; or output renders were simulated rather than produced and inspected multimodally; or the artifact fails runtime execution, fails test suites, misses stated requirements, or contradicts empirical evidence.

## Output contract

The structured QA handback containing the per-requirement / per-criterion verification table with pinpoint evidence citations, rendered output and test run observations, and exactly one verdict token (`PASS`, `REVISE`, or `FAIL`). Every requirement and criterion must be accounted for, none silently dropped. A report missing evidence for a `MET` criterion is not a pass. If no specifications/criteria exist, or if any criterion is `UNMET` or the check fails, release the QA task as `failed` with failure evidence and root cause documented on the record; do not file fix tasks or follow-up tasks. When all criteria are `MET`, release as `done`.

## When to include

Any workflow that produces a deliverable, specification, code change, or empirical report requiring verification against stated requirements and primary evidence before acceptance or merge.
