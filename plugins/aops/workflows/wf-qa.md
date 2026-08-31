---
title: Multi-Lens QA Gate
type: template
category: gate
description: Structured QA gate with depth modes (smoke, standard, deep) to evaluate an artifact against explicit criteria using an independent reviewer lens. Select when quality evaluation requires dedicated review. Not for simple sanity checks (use `wf-verification`).
tags: [qa, quality, review-lens, gate]
---

# Gate: Multi-Lens QA Gate

Structured quality review obligation with explicit criteria locking, evidence collection, and formal verdict.

## 1. Lock Criteria and Select Review Lens

- Lock acceptance criteria and select the review lens (`<lens>`) appropriate for the artifact type:
  - `Correctness / Logic`: Functionality, edge cases, failure modes.
  - `Security / Rules`: Axiom compliance, access controls, injection risks.
  - `Craft / Readability`: Instruction craftsmanship, concision, ergonomics.
- Set verification depth (`<depth>`): `smoke` (sanity), `standard` (full checks), `deep` (boundary stress).

## 2. Gather Independent Evidence

- An independent evaluator collects primary evidence: execution logs, diff inspections, or rendered outputs for `<artifact>`.
- The author/producer does not self-certify.

## 3. Judge and Emit Structured Verdict

- Evaluate gathered evidence against locked criteria.
- Emit structured verdict:
  - `PASS`: All criteria met with verified evidence.
  - `FAIL`: One or more criteria unmet; emit specific failure citations and required fixes.
  - `ESCALATE`: Contradiction or blocking ambiguity requiring principal decision.

## Exit Condition

`PASS` verdict reached, or route to `wf-refine-loop` on `FAIL`.
