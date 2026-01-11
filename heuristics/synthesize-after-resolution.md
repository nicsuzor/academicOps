---
name: synthesize-after-resolution
title: Synthesize After Resolution
number: 23
type: heuristic
category: spec
tags: [framework, heuristics, documentation]
---

# Synthesize After Resolution

**Statement**: Strip deliberation from specs. Keep only the resolved decisions.

## Derivation

Deliberation noise obscures decisions. Clean specs are easier to understand and maintain.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
