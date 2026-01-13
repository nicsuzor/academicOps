---
name: minimal-instructions
title: Minimal Instructions
priority: 44
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, efficiency]
---

# Minimal Instructions

**Statement**: Framework instructions should be no more detailed than required.

## Corollaries

- Brevity reduces cognitive load and token cost
- If it can be said in fewer words, use fewer words
- Don't read files you don't need to read

## Derivation

Long instructions waste tokens and cognitive capacity. Concise instructions are more likely to be followed.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Hard gate via `policy_enforcer.py` enforcing 200-line limit at PreToolUse. See [[RULES.md]].
