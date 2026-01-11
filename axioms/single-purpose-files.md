---
name: single-purpose-files
title: Single-Purpose Files
number: 10
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, organization]
---

# Single-Purpose Files

**Statement**: Every file has ONE defined audience and ONE defined purpose. No cruft, no mixed concerns.

## Derivation

Mixed-purpose files confuse readers and make maintenance harder. Clear boundaries enable focused work.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Hard gate via `policy_enforcer.py` enforcing 200-line limit at PreToolUse. See [[RULES.md]].
