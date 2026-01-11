---
name: verification-before-assertion
title: Verification Before Assertion
number: 3
type: heuristic
category: spec
tags: [framework, heuristics, verification]
---

# Verification Before Assertion

**Statement**: Agents must run verification commands BEFORE claiming success, not after.

## Derivation

Claiming success without verification leads to false confidence. Verification-first ensures claims are grounded in evidence.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Detection via `session_reflect.py` and custodiet periodic check at Stop/PostToolUse. See [[RULES.md]].
