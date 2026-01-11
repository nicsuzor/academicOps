---
name: just-in-time-context
title: Just-In-Time Context
number: 25
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, context]
---

# Just-In-Time Context

**Statement**: Context surfaces automatically when relevant. Missing context is a framework bug.

## Derivation

Agents cannot know what they don't know. The framework must surface relevant information proactively.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Automatic via `sessionstart_load_axioms.py` at SessionStart. See [[RULES.md]].
