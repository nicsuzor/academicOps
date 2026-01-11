---
name: check-docs-before-guessing
title: Check Documentation Before Guessing Syntax
number: 3a
type: heuristic
category: spec
parent: verification-before-assertion
tags: [framework, heuristics, verification]
---

# Check Documentation Before Guessing Syntax

**Statement**: When uncertain about tool/command syntax, CHECK documentation (--help, guides, MCP tools) instead of saying "maybe." Never guess tool behavior.

## Derivation

Guessed syntax wastes cycles on trial-and-error. Documentation provides authoritative answers.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Variant of [[verification-before-assertion]]. See [[RULES.md]].
