---
name: llm-semantic-evaluation
title: LLM Semantic Evaluation Over Keyword Matching
number: 37
type: heuristic
category: spec
tags: [framework, heuristics, verification]
---

# LLM Semantic Evaluation Over Keyword Matching

**Statement**: When verifying outcomes, use LLM semantic understanding to evaluate whether the INTENT was satisfied. NEVER use keyword/substring matching.

## Derivation

Keyword matching creates Volkswagen tests that pass on surface patterns without verifying actual behavior.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Review via PR template checklist and critic agent. See [[RULES.md]].
