---
name: avoid-namespace-collisions
title: Avoid Namespace Collisions
number: 8
type: heuristic
category: spec
tags: [framework, heuristics, naming]
---

# Avoid Namespace Collisions

**Statement**: Use unique names across all namespaces (skills, commands, hooks, agents).

## Derivation

Name collisions cause routing ambiguity and unexpected behavior. Unique names ensure predictable resolution.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
