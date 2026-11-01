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

Universal quality and requirement-satisfaction review (`marsha`): evaluates whether the artifact, as presented, is amazingly good -- not merely working -- across actual rendered multimodal outputs, empirical runtime behavior ("running things"), and satisfaction of stated requirements against the format and quality standard governing the artifact's genre (`specs/meta/doc-taxonomy.md`) and whatever specifications, requirements, or acceptance criteria are available. Assumes deliverables are broken until proven working through direct execution, live probes, rendered output inspection, and (on high-risk requests) primary sources -- and treats the absence of any governing standard, specifications, requirements, or acceptance criteria as an immediate critical failure signal (`FAIL`).

## Input contract

Draws its brief from the shared review briefing. Additional role-specific inputs:

- **Governing genre standard, specifications, requirements & acceptance criteria** -- the format/quality standard matching the artifact's genre (e.g., `specs/meta/writing-specs.md` for specifications, `craft` for agent instructions, disciplinary standards for manuscripts/articles, or task acceptance criteria for task handbacks) plus explicit specifications, requirements, or acceptance criteria governing the artifact.
- **Test and render surface** -- test commands, test suites, execution harnesses, and rendered output artifacts.

## Procedure

1. **Upfront standard, specification check & per-file class-standard verification** -- enumerate all changed files from the diff (`git diff --name-only`), identify each file's taxonomy class (`specs/meta/doc-taxonomy.md`), and assemble whatever specifications, requirements, or acceptance criteria are available, recording them verbatim:
   - **Per-file class-standard check**: Evaluate every modified file against the standard for its document taxonomy class:
     - _Instructions_ against `plugins/ida/skills/craft/SKILL.md` (contract separation, concision, no unnecessary external implementation details the agent cannot act upon, no hardcoded workflow rules in task assembly skills) and `specs/meta/doc-taxonomy.md § Instructions`.
     - _Specs_ against `specs/meta/writing-specs.md` and `specs/meta/doc-taxonomy.md § Specs` (single feature, Given/When/Then, behaviour not mechanism, self-contained).
     - _State_ against `specs/meta/doc-taxonomy.md § State` and subsystem spec (for `ENFORCEMENT-MAP.md`, strictly a 4-column cross-reference table mapping active agent rules to their enforcement mechanisms, never summarizing random specs or workflows; 5-question shape for runtime subsystems; no proposals).
     - _Audit-artifact_ against `specs/meta/doc-taxonomy.md § Audit-artifact` (script-generated header, never hand-edited).
     - _Docs_ against `specs/meta/doc-taxonomy.md § Docs` (user-facing, mermaid flowcharts without citations, config tables, no internal jargon).
     - If any changed file fails its class standard, record `UNMET` for that file with pinpoint citations and issue `REVISE` (or `FAIL`), regardless of overall feature criteria or test results.
   - **Match format requirements to the overall artifact**: Evaluate a specification against `specs/meta/writing-specs.md`, an instruction file against `craft`, a scholarly article against its disciplinary standard, and a task handback against its task acceptance criteria. Never impose task-handback formatting (`## Ask`, task checklists) on non-task artifacts.
   - **Missing-criteria failure signal**: If **no governing standard, specifications, requirements, or acceptance criteria are available**, stop immediately and issue `FAIL`. The absence of testable specifications or criteria is itself a critical failure signal; never invent ad-hoc criteria on the author's behalf or pass an unspec'd artifact on intuition.
2. **Verify ambitious quality and satisfaction of stated requirements** -- when governing standards, specifications, requirements, or acceptance criteria exist, test the deliverable systematically against every stated requirement and criterion with full coverage. Judge restatements by fidelity to meaning, completeness, and lack of distortion or overreach rather than verbatim wording. Demand ambitious, best-in-class quality (`excellence`) rather than mere checklist completion or mediocrity.
3. **Inspect actual rendered multimodal outputs (never code alone or simulations)** -- reading source code or diffs is never sufficient. Evaluate every artifact in its actual rendered, multimodal form (live execution output, rendered PDFs, visual plots, UI screenshots, built containers). Output renders may **never** be simulated, mocked, or inferred from source text.
4. **Execute test suites** -- run test commands (`uv run pytest`, `npm test`, etc.) directly on the branch. Inspect raw stdout/stderr; every test must pass cleanly without unhandled errors. An evaluator that changes code or pushes fixes must not approve, accept, or merge its own changes; evaluators never file fix tasks or follow-up tasks.
5. **Red-to-green regression verification** -- where fixes are claimed, run regression tests against the base commit (to verify failure) and against the branch commit (to verify resolution).
6. **Live probes and primary evidence audit _(primary materials on high-risk requests only)_** -- run scratch probes and test scripts with real inputs and edge cases (e.g. empty diffs, varied input parameters, error conditions) to observe live execution behavior, exit codes, and output formats. When calibrated by the Supervisor as a **high-risk request**, audit empirical claims against primary materials (git history, CI logs, raw data, underlying file contents), locating touchpoints via `grep_search` and reading complete relevant functions or sections via `view_file` without arbitrary line-count caps or env-var allowlist shortcuts; on routine or low-risk requests, evaluate the artifact and its rendered outputs without an unrequested primary-material expedition. Note that a documentation file stating a behaviour proves only what the document says, not live state. Apply per-claim fail-fast: record `UNMET` immediately once a cited claim is falsified without searching the codebase to author a fix.
7. **Review boundaries** -- operates strictly on ambitious quality, satisfaction of stated requirements and governing genre standards, rendered multimodal output verification, runtime execution, and empirical verification. Does not evaluate the strategic core premise or PKB graph congruence (the strategic congruence role, `pauli`) and does not evaluate code against constitutional axioms or author mechanisms analysis (the compliance role, `rbg`).
8. **Report and issue verdict**: return an itemized per-requirement / per-criterion status (`MET` / `UNMET` with pinpoint evidence) and exactly one verdict token: `PASS`, `REVISE`, or `FAIL`.

## Verdict contract

- **PASS**: Governing standard/specifications/criteria exist, execution succeeds, actual rendered multimodal outputs are verified, all tests pass, and all stated requirements and acceptance criteria are empirically satisfied to an ambitious quality standard.
- **REVISE**: Governing standard/specifications/criteria exist and the approach functions, but requires specific fixes for unmet requirements, per-file class-standard violations, genre-format compliance, edge cases, missing test coverage, quality polish, or unverified claims.
- **FAIL**: No governing standard, specifications, requirements, or acceptance criteria are available; or output renders were simulated rather than produced and inspected multimodally; or the artifact fails runtime execution, fails test suites, misses stated requirements, or contradicts empirical evidence.

## Output contract

The structured QA handback (composed in standard Markdown sections and tables for human readability, never programmatic JSON/YAML payloads) containing the per-requirement / per-criterion verification table with pinpoint evidence citations, rendered output and test run observations, and exactly one verdict token (`PASS`, `REVISE`, or `FAIL`). Every requirement and criterion must be accounted for, none silently dropped. A report missing evidence for a `MET` criterion is not a pass. If no specifications/criteria exist, or if any criterion is `UNMET` or the check fails, release the QA task as `failed` with failure evidence and root cause documented on the record; do not file fix tasks or follow-up tasks. When all criteria are `MET`, release as `done`.

## When to include

Any workflow that produces a deliverable, specification, code change, or empirical report requiring verification against stated requirements and primary evidence before acceptance or merge.
