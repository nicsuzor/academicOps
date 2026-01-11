---
name: semantic-link-density
title: Semantic Link Density
number: 34
type: heuristic
category: spec
tags: [framework, heuristics, documentation, links]
---

# Semantic Link Density

**Statement**: Related files MUST link to each other. Orphan files break navigation.

## Derivation

Links create navigable knowledge graphs. Orphans are undiscoverable.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Detection via `check_orphan_files.py` at Pre-commit. See [[RULES.md]].
