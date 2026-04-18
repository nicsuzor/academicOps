---
name: enforcement-map
title: Enforcement Map
type: state
category: state
description: How framework rules are enforced. Axioms are inviolable and enforced by the rbg agent.
permalink: enforcement-map
tags: [framework, enforcement]
---

# Enforcement Map

## Universal Axioms

**Source**: `aops-core/AXIOMS.md` (canonical, plugin-relative).
**Optional project supplement**: `.agents/rules/AXIOMS.md` in the working directory — adds, never overrides.
**Reader**: only the `rbg` agent. No other agent loads axiom content.

## Enforcement Mechanism

| Layer       | Mechanism                                                                                          |
| ----------- | -------------------------------------------------------------------------------------------------- |
| Periodic    | The `enforcer` gate fires at intervals and requires `rbg` invocation. Tools block until satisfied. |
| Targeted    | Other agents invoke `rbg` for axiom-derivation or compliance checks when needed.                   |
| Hard blocks | `policy_enforcer.py` denies specific destructive operations at PreToolUse.                         |
| Heuristics  | Advisory guidance in `HEURISTICS.md` — informs, does not block.                                    |

## Open Items

- Exact invocation cadence and trigger rules for the `enforcer` gate are still being formalised.
- Project-local axioms (`.agents/rules/AXIOMS.md`) loading is `rbg`-only — see `aops-core/agents/rbg.md`.
- GHA agents (built into `scripts/build.py`) are intended to follow `rbg` precisely; the inlining mechanism is left as-is for now.
