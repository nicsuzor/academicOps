---
name: skills-are-read-only
title: Skills Are Read-Only
priority: 23
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, skills]
---

# Skills Are Read-Only

**Statement**: Skills MUST NOT contain dynamic data. All mutable state lives in $ACA_DATA.

## Derivation

Skills are framework infrastructure shared across sessions. Dynamic data in skills creates state corruption and merge conflicts.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Hard gate via `settings.json` denying skill writes at PreToolUse. See [[enforcement-map.md]].
