---
name: q
type: command
category: instruction
description: Quick-queue a task — delegates to planner capture mode
triggers:
  - "/q"
  - "quick queue"
modifies_files: true
needs_task: false
mode: conversational
domain:
  - planning
---

# /q - Quick Queue

Delegate to the planner skill in **capture** mode.

Invoke: `Skill(skill="planner", args="capture: <user args>")`

Pass through all arguments exactly as the user provided them. If no arguments were given, invoke with just `Skill(skill="planner", args="capture")` — the planner will prompt for details.

Do not reimplement task capture here. The planner owns the workflow.
