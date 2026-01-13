---
name: mandatory-second-opinion
title: Mandatory Second Opinion
priority: 29
type: heuristic
category: spec
tags: [framework, heuristics, planning, review]
---

# Mandatory Second Opinion

**Statement**: Plans must be reviewed by critic agent before presenting to user.

## Derivation

Self-review misses blind spots. Independent review catches errors and unstated assumptions.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Soft gate via planner agent invoking critic at Planning phase. See [[RULES.md]].
