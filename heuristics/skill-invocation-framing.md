---
name: skill-invocation-framing
title: Skill Invocation Framing
number: 1
type: heuristic
category: spec
tags: [framework, heuristics, skills]
---

# Skill Invocation Framing

**Statement**: When directing an agent to use a skill, explain it provides needed context and use explicit syntax: `call Skill(name) to...`

## Derivation

Explicit syntax ensures skill invocation is recognizable and parseable. Context explanation helps agents understand why the skill matters.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Soft gate via `prompt-hydrator` guidance at UserPromptSubmit. See [[RULES.md]].
