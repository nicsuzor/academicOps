---
name: no-llm-calls-in-hooks
title: No LLM Calls in Hooks
number: 31
type: heuristic
category: spec
tags: [framework, heuristics, hooks]
---

# No LLM Calls in Hooks

**Statement**: Hooks never call LLM directly. Spawn background subagent instead.

## Derivation

LLM calls in hooks block the main agent. Background subagents enable parallel processing.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
