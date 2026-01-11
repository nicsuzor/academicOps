---
name: distinguish-script-vs-llm
title: Distinguish Script Processing from LLM Reading
number: 18
type: heuristic
category: spec
tags: [framework, heuristics, scripts]
---

# Distinguish Script Processing from LLM Reading

**Statement**: Document whether content is for script processing or LLM reading. Workflow differs.

## Derivation

Scripts parse structured data. LLMs understand prose. Mixing formats causes both to fail.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
