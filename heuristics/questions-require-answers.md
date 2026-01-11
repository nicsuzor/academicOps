---
name: questions-require-answers
title: Questions Require Answers, Not Actions
number: 19
type: heuristic
category: spec
tags: [framework, heuristics, interaction]
---

# Questions Require Answers, Not Actions

**Statement**: When user asks a question, ANSWER first. Do not jump to implementing or debugging. After reflection, STOP - do not proceed to fixing unless explicitly directed.

## Derivation

Users often want understanding before action. Jumping to fixes skips the learning step.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart; custodiet periodic check at PostToolUse. See [[RULES.md]].
