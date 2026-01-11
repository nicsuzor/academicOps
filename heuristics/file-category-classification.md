---
name: file-category-classification
title: File Category Classification
priority: 56
type: heuristic
category: spec
tags: [framework, heuristics, organization]
---

# File Category Classification

**Statement**: Every file has exactly one category (spec, ref, docs, script, instruction, template, state).

## Derivation

Mixed-category files are hard to maintain. Clear classification enables appropriate handling.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Detection via `check_file_taxonomy.py` at Pre-commit. See [[RULES.md]].
