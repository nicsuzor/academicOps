---
name: delete-dont-deprecate
title: Delete, Don't Deprecate
priority: 52
type: heuristic
category: spec
tags: [framework, heuristics, cleanup]
---

# Delete, Don't Deprecate

**Statement**: When consolidating files, DELETE old ones. Don't mark "superseded". Git has history.

## Derivation

Deprecated files create confusion and bloat. Git provides complete history for recovery.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
