---
name: use-askuserquestion
title: Use AskUserQuestion Tool for User Decisions
number: 16
type: heuristic
category: spec
tags: [framework, heuristics, interaction]
---

# Use AskUserQuestion Tool for User Decisions

**Statement**: When you need user input to proceed (clarification, choice between options, approval), use the AskUserQuestion tool. Questions in prose text get lost in transcripts.

## Derivation

Prose questions are easy to miss. The tool creates structured, visible decision points.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
