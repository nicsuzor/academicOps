---
name: research-data-immutable
title: Research Data Is Immutable
number: 24
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, research, data]
---

# Research Data Is Immutable

**Statement**: Source datasets, ground truth labels, records/, and any files serving as evidence for research claims are SACRED. NEVER modify, convert, reformat, or "fix" them.

## Corollary

If infrastructure doesn't support the data format, HALT and report the infrastructure gap. No exceptions.

## Derivation

Research integrity depends on data provenance. Modified source data invalidates all downstream analysis.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Hard gate via `settings.json` denying writes to `records/**` at PreToolUse. See [[RULES.md]].
