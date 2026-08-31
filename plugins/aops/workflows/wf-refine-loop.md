---
title: Drafter-Reviewer Refine Loop
type: template
category: gate
description: Convergence loop between drafter and independent reviewer when a review verdict is FAIL or REVISE. Select when iterating on an artifact until it passes quality gates. Not for initial drafting (use relevant process template).
tags: [refinement, iteration, convergence, review-loop, gate]
---

# Gate: Drafter-Reviewer Refine Loop

Iterative revision cycle to bring an artifact from initial failure to verified pass.

## 1. Ingest Review Findings

- Ingest structured failure findings and required remediations for `<artifact>`.
- Ensure each finding is actionable and unambiguous.

## 2. Targeted Remediation

- Drafter applies minimal targeted edits to address each cited defect.
- Maintain existing passing behaviors to avoid regressions.

## 3. Independent Re-Evaluation

- Independent reviewer re-evaluates the revised artifact against the original criteria.
- Gather fresh evidence; do not rely on prior round evaluations.

## 4. Convergence Check

- **Pass**: If all criteria met, loop terminates with approval.
- **Fail**: If criteria remain unmet and iteration count `< <max-rounds>`, repeat from step 1.
- **Escalate**: If progress stalls or exceeds `<max-rounds>`, escalate to operator.

## Exit Condition

`PASS` verdict from independent reviewer.
