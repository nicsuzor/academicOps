---
name: self-documenting
title: Self-Documenting
priority: 10
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, documentation]
---

# Self-Documenting

**Statement**: Documentation-as-code first; never make separate documentation files.

## Derivation

Separate documentation drifts from code. Embedded documentation stays synchronized with implementation.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Hard gate via `policy_enforcer.py` blocking `*-GUIDE.md` files at PreToolUse. See [[RULES.md]].
