---
name: no-horizontal-dividers
title: No Horizontal Line Dividers
priority: 63
type: heuristic
category: spec
tags: [framework, heuristics, markdown]
---

# No Horizontal Line Dividers

**Statement**: Use headings for structure, not horizontal lines (`---`, `***`, `___`). Horizontal lines are visual noise.

## Derivation

Headings provide semantic structure. Horizontal lines are purely visual and don't convey meaning.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Hard gate via markdownlint-cli2 at Pre-commit. See [[enforcement-map.md]].
