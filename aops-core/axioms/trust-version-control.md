---
name: trust-version-control
title: Trust Version Control
priority: 24
type: axiom
category: spec
inviolable: true
tags: [framework, principles, core, git]
---

# Trust Version Control

**Statement**: We work in git repositories - git is the backup system.

## Corollaries

- NEVER create backup files: `_new`, `.bak`, `_old`, `_ARCHIVED_*`, `file_2`, `file.backup`
- NEVER preserve directories/files "for reference" - git history IS the reference
- Edit files directly, rely on git to track changes
- Commit AND push after completing logical work units

## Derivation

Backup files create clutter and confusion. Git provides complete history with branching, diffing, and recovery.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Hard gate via `policy_enforcer.py` blocking backup patterns at PreToolUse. See [[enforcement-map.md]].
