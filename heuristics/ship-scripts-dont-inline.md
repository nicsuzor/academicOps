---
name: ship-scripts-dont-inline
title: Ship Scripts, Don't Inline Python
priority: 44
type: heuristic
category: spec
tags: [framework, heuristics, code]
---

# Ship Scripts, Don't Inline Python

**Statement**: Create scripts, never inline Python in markdown or prompts.

## Derivation

Inline code can't be tested or versioned. Scripts are reusable and maintainable.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
