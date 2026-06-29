---
name: issue-sweep
type: command
category: instruction
description: Thin shortcut — delegates to the survey skill in sweep mode. Autonomous GitHub issue triage that shrinks the backlog (consolidates/closes duplicates, aggregates related issues) — one cycle per invocation.
triggers:
  - "issue sweep"
  - "sweep issues"
  - "triage issues"
  - "drain issue backlog"
  - "process open issues"
modifies_files: true
needs_task: false
mode: execution
domain:
  - framework
  - operations
  - quality-assurance
allowed-tools: Agent
permalink: commands/issue-sweep
---

# /issue-sweep — Triage Backlog Issues

Triages GitHub issues by delegating to the `survey` skill in `sweep` mode. Triages ≤ 20 issues per cycle.

## Dispatch

Delegate the sweep execution to the Junior coordinator agent:
`Agent(subagent_type='junior', prompt='Run survey skill in sweep mode with [user arguments/focus]')`
