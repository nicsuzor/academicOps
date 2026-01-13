---
name: feedback-loops-for-uncertainty
title: Feedback Loops For Uncertainty
priority: 45
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, experimentation]
---

# Feedback Loops For Uncertainty

**Statement**: When the solution is unknown, don't guess - set up a feedback loop.

## Corollaries

- Requirement (user story) + failure evidence + no proven fix = experiment
- Make minimal intervention, wait for evidence, revise hypothesis
- Solutions emerge from accumulated evidence, not speculation

## Derivation

Guessing compounds uncertainty. Experiments with feedback reduce uncertainty systematically.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via AXIOMS.md at SessionStart. See [[RULES.md]].
