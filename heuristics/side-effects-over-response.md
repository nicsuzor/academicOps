---
name: side-effects-over-response
title: Side-Effects Over Response Text
number: 37d
type: heuristic
category: spec
parent: llm-semantic-evaluation
tags: [framework, heuristics, verification]
---

# Side-Effects Over Response Text

**Statement**: Use observable side-effects for verification, not response text parsing.

## Derivation

Response text can lie. Side-effects (files created, state changed) are ground truth.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Variant of [[llm-semantic-evaluation]]. See [[RULES.md]].
