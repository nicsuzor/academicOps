---
name: link-dont-repeat
title: Link, Don't Repeat
priority: 17
type: heuristic
category: spec
tags: [framework, heuristics, documentation]
---

# Link, Don't Repeat

**Statement**: Reference information rather than restating it. Brief inline context OK; multi-line summaries are not.

## Derivation

Repeated content drifts from source. Links maintain single source of truth and reduce maintenance burden.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
