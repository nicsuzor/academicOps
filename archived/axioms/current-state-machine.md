---
name: current-state-machine
title: Current State Machine
priority: 46
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, memory, knowledge]
---

# Current State Machine

**Statement**: $ACA_DATA is a semantic memory store containing ONLY current state. Episodic memory (observations) lives in bd issues.

## Derivation

Mixing episodic and semantic memory creates confusion. Current state should be perfect, always up to date, always understandable without piecing together observations.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Soft gate via `autocommit_state.py` (auto-commit+push) at PostToolUse. See [[RULES.md]].
