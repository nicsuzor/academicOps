---
name: execution-over-inspection
title: Execution Over Inspection
number: 37c
type: heuristic
category: spec
parent: llm-semantic-evaluation
tags: [framework, heuristics, verification]
---

# Execution Over Inspection

**Statement**: Compliance verification REQUIRES actual execution. Comparing fields, validating YAML, pattern matching specs - all are Volkswagen tests. The ONLY proof a component works is running it and observing correct behavior.

## Derivation

Inspection can pass while execution fails. Only execution proves functionality.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Prompt via framework skill compliance protocol. See [[RULES.md]].
