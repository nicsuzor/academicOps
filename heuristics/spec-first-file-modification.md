---
name: spec-first-file-modification
title: Spec-First File Modification
number: 35
type: heuristic
category: spec
tags: [framework, heuristics, specifications]
---

# Spec-First File Modification

**Statement**: Check/update governing spec first before modifying framework files.

## Derivation

Implementation without spec review leads to drift. Spec-first ensures changes align with design.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
