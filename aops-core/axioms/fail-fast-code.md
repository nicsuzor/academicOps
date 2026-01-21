---
name: fail-fast-code
title: Fail-Fast (Code)
priority: 8
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, code]
---

# Fail-Fast (Code)

**Statement**: No defaults, no fallbacks, no workarounds, no silent failures.

## Corollaries

- Fail immediately when configuration is missing or incorrect
- Demand explicit configuration

## Derivation

Silent failures mask problems until they compound catastrophically. Immediate failure surfaces issues when they're cheapest to fix.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Hard gate via `policy_enforcer.py` blocking destructive git commands at PreToolUse. See [[enforcement-map.md]].
