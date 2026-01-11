---
name: context-over-algorithms
title: Context Over Algorithms
priority: 27
type: heuristic
category: spec
parent: semantic-search-over-keyword
tags: [framework, heuristics, search]
---

# Context Over Algorithms

**Statement**: Give agents enough context to make decisions. Never use algorithmic matching (fuzzy, keyword, regex).

## Derivation

Algorithms can't understand intent. LLMs with context make better decisions than pattern matchers.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Variant of [[semantic-search-over-keyword]]. See [[RULES.md]].
