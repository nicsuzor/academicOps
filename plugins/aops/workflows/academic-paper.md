---
title: Academic Paper
type: template
category: process
description: Academic manuscript preparation from research outline to final submission artifact. Select when authoring, structuring, or revising research papers. Not for peer reviewing external manuscripts (use `peer-review` skill) or point-by-point reviewer rebuttals (use `review-response`).
tags: [academic, research, writing, manuscript, publication, process]
---

# Process: Academic Paper

End-to-end authoring and quality pipeline for academic research manuscripts.

## 1. Structural Map and Framing

- Define core research question, theoretical framing, empirical methodology, and novel contribution (`structural-map-extraction`).
- Establish section outline and target journal/conference formatting guidelines (`<target-venue>`).

## 2. Methodology and Empirical Pipeline

- Ensure underlying analysis pipeline and figures are reproducible and version-controlled.
- Verify data immutability and statistical rigor before integrating figures/tables into text.

## 3. Section Drafting

- Draft manuscript sections iteratively: Abstract, Introduction, Literature Review, Methodology, Empirical Results, Discussion, and Conclusion.
- Ensure logical flow, precision of language, and clear signposting between sections.

## 4. Fact and Citation Verification

- Compose `wf-fact-check` to verify every cited claim against primary literature.
- Ensure all equations, table numbers, and bibliographic entries resolve without errors.

## 5. Review and Submission Preparation

- Compose `wf-qa` with academic review lens to evaluate clarity, rigor, and contribution.
- Generate publication-ready PDF artifact and present to principal for submission sign-off (`wf-signoff-loop`).
