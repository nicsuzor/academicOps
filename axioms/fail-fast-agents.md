---
name: fail-fast-agents
title: Fail-Fast (Agents)
number: 8
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, agents]
---

# Fail-Fast (Agents)

**Statement**: When YOUR instructions or tools fail, STOP immediately.

## Corollaries

- Report error, demand infrastructure fix
- No workarounds, no silent failures

## Derivation

Agent workarounds hide infrastructure bugs that affect all future sessions. Halting forces proper fixes.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Soft gate via `fail_fast_watchdog.py` injecting reminder at PostToolUse. See [[RULES.md]].
