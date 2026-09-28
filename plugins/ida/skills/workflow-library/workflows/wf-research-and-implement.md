---
alias:
  - wf-research-and-implement
  - wf-research-implement
description: "Composed pipeline for research-and-implementation tasks: research, spec, review, human approval of the full spec, and implementation."
id: wf-research-and-implement
tags:
  - wf-template
  - composite
  - research
  - spec
  - implementation
title: wf-research-and-implement
type: template
---

## What this step does

Composes an end-to-end pipeline for tasks requiring research, specification, peer review, human approval, and implementation. Enforces strict stage ordering and requires human approval of the full specification before implementation can begin.

## Stages

Execution proceeds strictly in the following sequence:

1. **Research (`[[wf-research]]`)**
   Investigate the problem domain, survey codebase context and external options, evaluate trade-offs, and produce grounded research findings with primary citations.
2. **Write Spec (`[[wf-spec]]`)**
   Draft a comprehensive technical specification based on research findings, defining architecture, interface contracts, scope boundaries, test plans, and acceptance criteria.
3. **Review Research and Spec (`[[wf-qa]]`, `[[wf-fact-check]]`)**
   Conduct independent review of both the research and the specification:
   - Check factual, empirical, and citation-bearing claims against sources via `[[wf-fact-check]]`.
   - Evaluate spec completeness, architectural soundness, and testability against requirements via `[[wf-qa]]`.
   - Resolve any defects or gaps before advancing.
4. **Approval Gate (`[[wf-human-approval]]`)**
   Present the full specification (not a summary) to Nic for review and explicit approval. Implementation cannot start until Nic approves. If revisions are requested, address them in Stage 2 before resubmitting.
5. **Implementation (`[[wf-tdd]]`, `[[wf-qa]]`, `[[wf-signoff]]`)**
   Once approved, implement the specification:
   - Execute code changes under test-driven development (`[[wf-tdd]]`), maintaining green test suites.
   - Perform independent QA evaluation (`[[wf-qa]]`) against the spec's acceptance criteria.
   - Produce the delivery digest and receipts via `[[wf-signoff]]`.

## Constraints

- Strictly sequential: do not draft specs without research; do not begin implementation before explicit approval.
- The approval gate must present the full specification, never a summary.
- Implementation is blocked until human approval is confirmed on record.

## Output contract

- Grounded research findings with citations (`[[wf-research]]`).
- Full approved technical specification (`[[wf-spec]]`).
- Independent review verdicts (`[[wf-qa]]`, `[[wf-fact-check]]`).
- Recorded human approval decision (`[[wf-human-approval]]`).
- Tested implementation and QA report (`[[wf-tdd]]`, `[[wf-qa]]`).
- Final signoff brief (`[[wf-signoff]]`).

## When to include

Any initiative requiring investigation and specification prior to building (e.g. "research, design, and implement..."), ensuring design alignment before committing engineering effort.
