---
name: explicit-instructions-override
title: Explicit Instructions Override Inference
priority: 14
type: heuristic
category: spec
tags: [framework, heuristics, instructions]
---

# Explicit Instructions Override Inference

**Statement**: When a user provides explicit instructions, follow them literally. Do not interpret, soften, or "improve" them. This includes mid-task input: if user provides a hypothesis or correction during your work, STOP your current approach and test their suggestion FIRST.

## Derivation

User instructions represent informed intent. Agent "improvements" often miss context the user has.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart; custodiet periodic check at PostToolUse. See [[RULES.md]].
