---
name: acceptance-criteria-own-success
title: Acceptance Criteria Own Success
priority: 31
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, verification]
---

# Acceptance Criteria Own Success

**Statement**: Only user-defined acceptance criteria determine whether work is complete. Agents cannot modify, weaken, or reinterpret acceptance criteria. If criteria cannot be met, HALT and report.

## Derivation

Agents cannot judge their own work. User-defined criteria are the only valid measure of success.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Soft gate via `/qa` skill enforcement at Stop. See [[RULES.md]].
