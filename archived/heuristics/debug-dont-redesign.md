---
name: debug-dont-redesign
title: Debug, Don't Redesign
priority: 47
type: heuristic
category: spec
tags: [framework, heuristics, debugging]
---

# Debug, Don't Redesign

**Statement**: When debugging, propose fixes within current design. Don't pivot architectures without approval.

## Derivation

Redesign during debugging creates scope creep. Fix the bug first, then propose improvements separately.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
