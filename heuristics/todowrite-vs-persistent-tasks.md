---
name: todowrite-vs-persistent-tasks
title: TodoWrite vs Persistent Tasks
priority: 49
type: heuristic
category: spec
tags: [framework, heuristics, tasks]
---

# TodoWrite vs Persistent Tasks

**Statement**: TodoWrite for approved steps only. Use bd/tasks for work that spans sessions.

## Derivation

TodoWrite is ephemeral. Persistent work needs persistent tracking.

## Evidence

Evidence of violations and corrections tracked in bd issues (label: `learning`).

## Enforcement

Injected via HEURISTICS.md at SessionStart. See [[RULES.md]].
