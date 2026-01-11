---
name: skill-first-action
title: Skill-First Action
number: 2
type: heuristic
category: spec
tags: [framework, heuristics, skills]
---

# Skill-First Action

**Statement**: Almost all agent actions should follow skill invocation for repeatability.

## Derivation

Skills encode domain knowledge and best practices. Skipping skills means reinventing solutions and missing guardrails.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Soft gate via `prompt-hydrator` suggesting skills at UserPromptSubmit. See [[RULES.md]].
