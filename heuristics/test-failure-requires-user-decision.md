---
name: test-failure-requires-user-decision
title: Test Failure Requires User Decision
number: 38
type: heuristic
category: spec
tags: [framework, heuristics, testing]
---

# Test Failure Requires User Decision

**Statement**: When a test fails during verification, agents MUST report failure and STOP. Agents cannot modify test assertions, redefine success criteria, or rationalize failures as "edge cases." Only the user decides whether to fix the code, revise criteria, or investigate further.

## Derivation

Agents cannot judge their own work. Test failures require human judgment about next steps.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
