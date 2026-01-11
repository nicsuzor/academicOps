---
name: no-workarounds
title: No Workarounds
priority: 25
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, agents]
---

# No Workarounds

**Statement**: If your tooling or instructions don't work PRECISELY, log the failure and HALT. Don't work around bugs.

## Corollaries

- NEVER use `--no-verify`, `--force`, or skip flags to bypass validation
- NEVER rationalize bypasses as "not my fault" or "environmental issue"
- If validation fails, fix the code or fix the validator - never bypass it

## Derivation

Workarounds hide infrastructure bugs that affect all future sessions. Each workaround delays proper fixes and accumulates technical debt.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Soft gate via `fail_fast_watchdog.py` at PostToolUse. See [[RULES.md]].
