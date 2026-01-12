---
name: full-evidence-for-validation
title: Full Evidence for Human Validation
priority: 58
type: heuristic
category: spec
parent: llm-semantic-evaluation
tags: [framework, heuristics, verification]
---

# Full Evidence for Human Validation

**Statement**: Demo tests must expose the ENTIRE INTERNAL WORKING of the feature being demonstrated - all intermediate states, decision points, and data transformations. "Full output" means making the feature's internal machinery visible, not just printing the final response without truncation.

## Derivation

Hiding internal working prevents validation. Humans cannot judge correctness by seeing only final output - they need to see HOW the feature arrived at that output. Demo tests that only print final responses (even untruncated) are black boxes that don't demonstrate the feature's behavior.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Convention via `@pytest.mark.demo` requirement. See [[RULES.md]].
