---
name: indices-before-exploration
title: Indices Before Exploration
priority: 42
type: heuristic
category: spec
tags: [framework, heuristics, navigation]
---

# Indices Before Exploration

**Statement**: Check index files (ROADMAP.md, README.md, INDEX.md) before using glob/grep to explore.

## Derivation

Index files provide curated navigation. Blind exploration wastes cycles and misses structure.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
