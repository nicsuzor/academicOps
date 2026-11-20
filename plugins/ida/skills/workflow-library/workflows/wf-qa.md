---
alias:
  - wf-qa
  - wf-quality-review
description: Universal empirical QA verification -- verify deliverables through live test execution, probes, actual rendered multimodal outputs (never simulated), acceptance criteria, and applicable project document standards (treating missing criteria as FAIL), returning PASS, REVISE, or FAIL.
id: wf-qa
tags:
  - wf-template
  - review
  - qa
  - verification
  - requirements
title: Empirical QA Verification
type: template
---

## What this step does

Independent empirical and functional verification: assumes deliverables are broken until proven working through direct test execution, live probes, inspection of actual rendered outputs, verification against stated specifications/acceptance criteria and applicable project document standards, and (on high-risk requests) primary-material audits. Treats the absence of any governing standard, specification, requirements, or acceptance criteria as an immediate `FAIL`.

## Input contract

Draws its brief from the shared review briefing plus:

- **Governing standards & criteria**: applicable project document and genre standards, explicit specifications, requirements, and task acceptance criteria (never imposing task-handback checklists on non-task artifacts).
- **Test & render surface**: test commands, execution harnesses, and rendered output artifacts.

## Procedure

1. **Verify standards and criteria upfront** -- enumerate changed files and assemble governing genre standards, applicable project document standards, specifications, and acceptance criteria verbatim. If no governing standard, specification, or criteria exist, stop immediately and issue `FAIL` -- never invent ad-hoc criteria. If any changed file violates its applicable project document standard, record `UNMET` with pinpoint citations.
2. **Check requirement coverage** -- test deliverables systematically against every stated requirement and criterion (judging restatements by fidelity to meaning and completeness).
3. **Inspect actual rendered outputs** -- evaluate artifacts in their actual rendered multimodal form (live command output, rendered PDFs, plots, UI screenshots, built containers); never simulate, mock, or infer renders from source code alone.
4. **Run test suites & regression checks** -- execute test commands directly on the branch and inspect raw stdout/stderr; verify red-to-green regression behavior against base vs. branch commits when fixes are claimed.
5. **Run live probes & primary-material audit** -- probe real inputs and edge cases to observe exit codes and outputs. When calibrated high-risk by the coordinator, audit empirical claims against primary materials (git history, CI logs, raw data, complete relevant source files); treat documentation notes as proving only what the document says, not live state.
6. **Apply fix discipline & boundaries** -- apply uncontroversial deterministic fixes (`fix(review): <description>`) ONLY when serialized or explicitly authorized on a writable branch, itemizing them as Argdown observations internally (or under `### Reviewer Self-Fixes Applied` in published PR/issue or user-facing outputs); parallel or read-only passes report suggested fixes as Argdown findings internally (or under `### Suggested Fixes` in published/user-facing outputs) for the fix pass. Never author complex redesigns or file follow-up tasks. Judge strictly on empirical requirement satisfaction and applicable document standards (leaving strategic congruence and axiom compliance to their respective review roles).

## Verdict & output contract

- **PASS**: Governing standard/criteria exist, tests and probes pass, actual rendered outputs are verified, and every requirement is empirically `MET`.
- **REVISE**: Governing criteria exist and core approach functions, but specific unmet requirements, document-standard violations, edge cases, or missing verification remain.
- **FAIL**: No governing standard/criteria exist, renders were simulated rather than inspected, or the deliverable fails runtime execution, tests, or empirical checks.

Internal agent-to-agent QA handbacks report **only** in clean Argdown prose per `premise-check` (leading with original ask and verdict, quoting deciding test/render receipts inline); structured Markdown (never programmatic JSON/YAML) with `### Reviewer Self-Fixes Applied`, `### Suggested Fixes`, and a per-requirement verification table applies strictly to published PR/issue or user-facing outputs. Account for every requirement (`MET` / `UNMET` with pinpoint evidence, none silently dropped), test/render observations, any self-fixes, and one verdict (`PASS`, `REVISE`, or `FAIL`). Release headless QA tasks as `done` only when all criteria are `MET`; otherwise release as `failed` with root cause and failure evidence on the record.

## When to include

Any workflow producing a deliverable, specification, code change, or empirical report requiring independent verification against stated requirements and live evidence before acceptance or merge.
