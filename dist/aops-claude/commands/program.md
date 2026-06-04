---
name: program
type: command
category: instruction
description: Program / portfolio supervision — the autonomous top loop above /supervisor that drives a release-level goal across many epics
triggers:
  - "/program"
  - "ready the release"
  - "drive the release"
modifies_files: true
needs_task: true
mode: iterative
domain:
  - operations
owner: junior
permalink: commands/program
---

# /program — Program / Portfolio Supervision

Invoke the **program** skill. This is junior's autonomous top loop, one scope above `/supervisor`: it owns a release-level goal spanning many epics, discovers and decomposes the constituent epics itself, runs `/supervisor` per epic, and surfaces only escalations + merge-ready PRs.

Invoke: `Skill(skill="program", args="<program-task-id>")`

**Canonical loop invocation:** `/loop 30m /program <program-task-id>`

If no program task exists yet for the release goal, the skill's first tick discovers and files the constituent epics under a program task. The skill owns the workflow — do not reimplement the loop here.
