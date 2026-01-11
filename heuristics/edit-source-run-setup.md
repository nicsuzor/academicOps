---
name: edit-source-run-setup
title: Edit Source, Run Setup
number: 13
type: heuristic
category: spec
tags: [framework, heuristics, configuration]
---

# Edit Source, Run Setup

**Statement**: Never modify runtime config directly. Edit source files and run setup to regenerate.

## Derivation

Direct runtime edits get overwritten and create drift from source. Source-first ensures reproducibility.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
