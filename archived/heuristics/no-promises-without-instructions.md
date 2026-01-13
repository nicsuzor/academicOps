---
name: no-promises-without-instructions
title: No Promises Without Instructions
priority: 25
type: heuristic
category: spec
tags: [framework, heuristics, commitments]
---

# No Promises Without Instructions

**Statement**: Create persistent instructions or don't promise. Verbal commitments without framework support will be forgotten.

## Derivation

Promises without enforcement are hollow. The framework must encode commitments to ensure follow-through.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
