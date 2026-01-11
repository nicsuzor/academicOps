---
name: skills-no-dynamic-content
title: Skills Contain No Dynamic Content
number: 9
type: heuristic
category: spec
tags: [framework, heuristics, skills]
---

# Skills Contain No Dynamic Content

**Statement**: Current state lives in $ACA_DATA, not in skills.

## Derivation

Skills are shared framework infrastructure. Dynamic content in skills creates merge conflicts and state corruption.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Hard gate via `settings.json` denying skill writes at PreToolUse. See [[RULES.md]].
