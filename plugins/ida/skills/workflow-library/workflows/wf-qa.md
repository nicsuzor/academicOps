---
alias:
  - wf-qa
  - wf-quality-review
description: Universal runtime QA and functional verification review -- test runtime correctness, execute test suites, verify red-to-green regression proofs, probe behavioral edge cases, and confirm requirement satisfaction against specifications and acceptance criteria (treating their absence as FAIL), returning PASS, REVISE, or FAIL.
id: wf-qa
tags:
  - wf-template
  - review
  - qa
  - verification
  - requirements
title: Functional QA and Verification Review
type: template
---

## What this step does

Universal runtime QA and requirement-satisfaction review: verifies whether an implementation executes correctly, passes live test suites and regression proofs, handles behavioral edge cases, and satisfies stated specifications, requirements, and acceptance criteria. Assumes deliverables are broken until proven working through direct runtime execution and live evidence, treating absent specifications or acceptance criteria as an immediate `FAIL`.

## Input contract

Draws its brief from the shared review briefing. Additional role-specific inputs:

- **Specifications, requirements & acceptance criteria**: Explicit functional specifications, behavioral requirements, or acceptance criteria governing the deliverable (or explicit notice of their absence).
- **Execution and test surface**: Repository branch, build/test commands, runtime harness, and probe targets.

## Procedure

1. **Assemble specifications and acceptance criteria upfront**: Record the governing specifications, requirements, and acceptance criteria verbatim. If none are available, stop immediately and issue `FAIL`; never invent ad-hoc criteria or pass unspec'd behavior on intuition.
2. **Verify systematic requirement coverage**: Test the implementation against every stated functional requirement and acceptance criterion with full coverage, judging semantic completeness and accuracy without distortion or overreach.
3. **Execute directly (never code-reading or simulations)**: Reading source code, diffs, or mocked outputs never proves runtime correctness. Run the actual commands, built artifacts, and execution paths directly and inspect raw stdout, stderr, and exit codes.
4. **Run test suites**: Execute relevant test commands (`uv run pytest`, `npm test`, etc.) directly on the branch. Every test must pass cleanly without unhandled errors or silently skipped assertions. Reviewers may apply uncontroversial deterministic test or build repairs directly, commit (`fix(review): ...`), and push so `HEAD` matches tested state, without authoring complex functional redesigns or minting follow-up tasks.
5. **Verify red-to-green regressions**: Where bug fixes or behavioral changes are claimed, run regression tests against the base commit (confirming reproduction) and against the branch commit (confirming resolution).
6. **Probe behavioral edge cases and empirical claims**: Run live probes with varied inputs and error paths (empty inputs, boundaries, malformed states, failure conditions) to observe exit codes, error handling, and outputs. Verify empirical claims directly against primary runtime or data evidence using targeted full-context reads rather than documentation claims alone.
7. **Report spec-compliant findings only**: When checks fail, record `UNMET` with reproduction steps, raw output, and root cause; never emit or recommend remediation options that relax specifications, bypass rules, or violate governing constraints. Route compliance or rule-interpretation questions to compliance review.
8. **Respect review boundaries and issue verdict**: Confine evaluation strictly to runtime functional correctness, test execution, regression verification, behavioral edge cases, and requirement satisfaction. Do not perform qualitative taste/editorial evaluation (qualitative review), axiom/authority/rule checks (compliance review), or strategic/PKB congruence review (strategic review). Return one verdict (`PASS`, `REVISE`, or `FAIL`).

## Verdict contract

- **PASS**: Specifications/criteria exist, direct execution succeeds, all test suites and regression proofs pass, edge cases hold, and all stated requirements are empirically `MET`.
- **REVISE**: Specifications/criteria exist and core behavior runs, but specific unmet functional requirements, failing edge cases, missing test coverage, or unverified runtime claims require fixes.
- **FAIL**: No specifications, requirements, or acceptance criteria exist; runtime execution was simulated instead of observed; or test suites, core functional requirements, or empirical checks fail.

## Output contract

Human-readable Markdown report containing `### Reviewer Self-Fixes Applied` (if any, committed and pushed), the itemized per-requirement / per-criterion table (`MET` / `UNMET` with pinpoint runtime evidence), executed test and probe observations, and one verdict token (`PASS`, `REVISE`, or `FAIL`). Release the QA task as `done` only when all criteria are `MET` and checks pass; otherwise release as `failed` with root-cause evidence on the record without minting follow-up tasks.

## When to include

Any workflow producing runnable code, scripts, tooling, or empirical changes requiring live functional verification and test proofs before acceptance or merge.
