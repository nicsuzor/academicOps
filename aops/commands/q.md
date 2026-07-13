---
name: q
type: command
category: instruction
description: Quick-queue a task — delegates to the situate skill
triggers:
  - "/q"
  - "quick queue"
modifies_files: true
needs_task: false
mode: conversational
domain:
  - planning
allowed-tools: Skill
permalink: commands/q
---

# /q — Quick Queue

Captures a task by delegating to the `situate` skill.

## Execution

Invoke the situate skill:
`Skill(skill="situate", args="<user args>")`

Pass all arguments exactly as provided. If no arguments are given, run:
`Skill(skill="situate")`
