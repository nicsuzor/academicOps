---
alias:
  - wf-qa
  - wf-quality-review
description: Universal empirical QA verification -- verify the real artifact as its audience meets it (never a stand-in, sample data, or simulated render) through live test execution, probes, actual rendered multimodal outputs, acceptance criteria, and applicable project document standards (treating missing criteria as FAIL), returning PASS, REVISE, or FAIL.
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

## The real artifact

QA judges the real artifact as its audience meets it: what the real pipeline produced from real inputs, obtained where its audience gets it. A stand-in decides nothing -- a locally started server, sample or fixture data, a mock, or a rendering made for the review proves only itself. Which artifact is real, and where it lives, come from the instantiating task or the project's record of its live targets, never from this template. Obtaining it is the one step that varies by kind:

- **A deployed service or page**: its live address, reached through the access the environment provides.
- **A built file** (PDF, document, image, plot): the project's own build run on the real inputs, and the output opened.
- **Published or sent text**: the copy as published or sent.

If the real artifact cannot be reached or built, halt: report the response verbatim and release the task `blocked`. Never substitute a stand-in to keep going.

## Input contract

Draws its brief from the shared review briefing plus:

- **Governing standards & criteria**: applicable project document and genre standards, explicit specifications, requirements, and task acceptance criteria (never imposing task-handback checklists on non-task artifacts).
- **Test & render surface**: test commands, execution harnesses, and rendered output artifacts.

## Procedure

1. **Verify standards and criteria upfront** -- enumerate changed files and assemble governing genre standards, applicable project document standards, specifications, and acceptance criteria verbatim. If no governing standard, specification, or criteria exist, stop immediately and issue `FAIL` -- never invent ad-hoc criteria. If any changed file violates its applicable project document standard, record `UNMET` with pinpoint citations.
2. **Check requirement coverage** -- test deliverables systematically against every stated requirement and criterion (judging restatements by fidelity to meaning and completeness).
3. **Inspect actual rendered outputs** -- obtain the real artifact (**The real artifact**, above) and evaluate it in its actual rendered multimodal form (live command output, rendered PDFs, plots, UI screenshots, built containers); never simulate, mock, substitute a stand-in, or infer renders from source code alone. Judge what the output delivers to its audience, not only how it looks: a clean render that fails its purpose is `UNMET`.
4. **Run test suites & regression checks** -- execute test commands directly on the branch and inspect raw stdout/stderr; verify red-to-green regression behavior against base vs. branch commits when fixes are claimed.
5. **Run live probes & primary-material audit** -- probe real inputs and edge cases to observe exit codes and outputs. When calibrated high-risk by the coordinator, audit empirical claims against primary materials (git history, CI logs, raw data, complete relevant source files); treat documentation notes as proving only what the document says, not live state.
6. **Apply fix discipline & boundaries**:
   - Apply uncontroversial deterministic fixes (`fix(review): <description>`) only when serialized or explicitly authorized on a writable branch, itemizing applied fixes; parallel or read-only passes itemize suggested fixes for the fix pass instead.
   - Never author complex redesigns or file follow-up tasks; judge strictly on empirical requirement satisfaction and applicable document standards (leaving strategic congruence and axiom compliance to their respective review roles).

## Verdict & output contract

- **PASS**: Governing standard/criteria exist, tests and probes pass, actual rendered outputs are verified, and every requirement is empirically `MET`.
- **REVISE**: Governing criteria exist and core approach functions, but specific unmet requirements, document-standard violations, edge cases, or missing verification remain.
- **FAIL**: No governing standard/criteria exist, renders were simulated or judged on a stand-in rather than the real artifact, or the deliverable fails runtime execution, tests, or empirical checks.

- **Format boundary**: Internal QA handbacks report **only** in clean Argdown prose per `premise-check` (upfront ask and verdict, inline test/render receipts); structured Markdown (never JSON/YAML) with `### Reviewer Self-Fixes Applied`, `### Suggested Fixes`, `### Required Changes`, and a per-requirement table applies strictly to published PR/issue or user-facing outputs.
- **Required content & release**: Account for every requirement (`MET` / `UNMET` with pinpoint evidence, none dropped), test/render receipts, self-fixes or suggested fixes, and one verdict (`PASS`, `REVISE`, or `FAIL`). Release headless QA tasks as `done` only when all criteria are `MET`; otherwise release as `failed` with root cause and failure evidence.

## After a failing verdict

The supervising executor, not the reviewer, acts on a `REVISE` or `FAIL`. Where the defect lies within the task's scope and reach, they fix it and send the real artifact back through QA. Otherwise they release the task `failed` (the deliverable is wrong) or `blocked` (the cause lies outside it), with a follow-up task for the change elsewhere when one is needed.

## When to include

Any workflow producing a deliverable, specification, code change, or empirical report requiring independent verification against stated requirements and live evidence before acceptance or merge.
