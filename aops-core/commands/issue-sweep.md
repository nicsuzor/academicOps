---
name: issue-sweep
type: command
category: instruction
description: Thin shortcut — delegates to the triage skill in sweep mode. Autonomous GitHub issue triage that shrinks the backlog (consolidates/closes duplicates, aggregates related issues) — one cycle per invocation.
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

Triages GitHub issues by delegating to the `triage` skill in `sweep` mode. Triages ≤ 20 issues per cycle.

## Dispatch

Delegate the sweep execution to Pauli (issue consolidation, single-task filing, and fix-epic decomposition are graph-mutation work inside Pauli's existing charter — see `specs/agents/pauli.md`):
`Agent(subagent_type='pauli', model='sonnet', prompt='Run triage skill in sweep mode with [user arguments/focus]')`
