---
name: context-uncertainty-favors-skills
title: Context Uncertainty Favors Skills
number: 6
type: heuristic
category: spec
tags: [framework, heuristics, skills]
---

# Context Uncertainty Favors Skills

**Statement**: When uncertain whether a task requires a skill, invoke it. The cost of unnecessary context is lower than missing it.

## Derivation

Skills provide guardrails and domain knowledge. False negatives (missing skill) cause more harm than false positives (extra context).

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Soft gate via `prompt-hydrator` guidance at UserPromptSubmit. See [[RULES.md]].
