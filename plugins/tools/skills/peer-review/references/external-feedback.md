---
title: External & Cross-model Feedback
permalink: external-feedback
tags: [reference, peer-review, external-feedback]
---

# Integrating External & Cross-Model Feedback

Integrate external reviews and cross-model passes using a distrust-default stance. Cross-model feedback provides value through distillation of analytical style and emphasis corroboration, not new evidence. In-loop adversarial verification remains the primary safety net.

## Per-Claim Adjudication

Decompose external feedback into atomic claims and evaluate each against the primary source:

- **TRUE**: Supported by application evidence; cite the source reference.
- **PARTIALLY**: Contains valid points but is overstated or misdirected.
- **FALSE**: Directly contradicted by application text.
- **OVERSTATED**: Directionally valid, but claims exceed available evidence.
- **NOT-FOUND**: Elements not present in the application.

Assign an action with a one-line rationale:

- **ADD**: Adopt verified, non-redundant feedback.
- **MODIFY**: Concede valid points while preserving essential critique.
- **REJECT**: Exclude inaccurate, unsupported, or redundant claims (require 1-line justification).

## Two-Axis Evaluation Filter

Evaluate every external claim across two axes:

1. **Truth**: Accurate against application text.
2. **Redundancy**: Reject if already captured more sharply in the draft.
3. **Conflict check**: Does the claim reverse an established weakness into praise? Flag all conflicts directly to the human reviewer; never resolve them silently.

## Corpus-Level Consistency

When external feedback addresses multiple reviews within a round, evaluate phrase repetition and consistency as a whole-set pass across all documents ([[voice-and-detemplating]]), rather than per-application silos.
