---
name: mandatory-acceptance-testing
title: Mandatory Acceptance Testing
priority: 48
type: heuristic
category: spec
tags: [framework, heuristics, testing]
---

# Mandatory Acceptance Testing

**Statement**: Feature development includes acceptance tests. No feature is complete without verification.

## Derivation

Untested features may not work. Acceptance tests prove the feature meets requirements.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Soft gate via `/qa` skill at Stop. See [[RULES.md]].
