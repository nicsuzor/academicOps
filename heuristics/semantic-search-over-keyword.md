---
name: semantic-search-over-keyword
title: Semantic Search Over Keyword Matching
number: 12
type: heuristic
category: spec
tags: [framework, heuristics, search, memory]
---

# Semantic Search Over Keyword Matching

**Statement**: Use memory server for semantic search, never grep markdown for knowledge retrieval.

## Derivation

Keyword matching misses semantically related content. Semantic search understands intent and context.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
