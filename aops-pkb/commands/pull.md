---
name: pull
type: command
category: instruction
description: Claim the next queued task and run it INLINE in this interactive session — with licence to ask the user questions. Thin alias over the task-lifecycle skill's execute mode. For background dispatch use /dispatch.
triggers:
  - "pull task"
  - "get work"
  - "what should I work on"
  - "next task"
  - "claim and run a task"
modifies_files: true
needs_task: false
mode: execute
domain:
  - operations
allowed-tools: Skill
permalink: commands/pull
---

# /pull — Claim and Run the Next Queued Task Inline

Selects the next queued task and **runs it in the current interactive session**:
claim → execute → verify → complete. Because this is interactive, you may ask the
user questions whenever a decision is genuinely theirs. To hand work to a
background worker instead, use `/dispatch`.

## Execution

Delegate to the `task-lifecycle` skill in `execute` mode, passing all arguments
exactly as provided:

`Skill(skill="task-lifecycle", args="execute: <user args>")`

If no arguments are given, run:

`Skill(skill="task-lifecycle", args="execute")`

<!-- NS/build: the aops-core `<!-- cowork:only --> ... <!-- /cowork:only -->`

marker convention (build_aops_core's cowork build strips/keeps these blocks)
does not exist in aops-pkb's build yet — this plugin has no "cowork" platform
build. The prior Cowork native-list-mirror paragraph (driven by aops-core's
`cowork-sync` skill, itself overlaid from the aops-cowork package) was dropped
here rather than shipped inert. If aops-pkb ever needs a Cowork build, port the
marker-processing step from scripts/build.py's build_aops_core and re-add the
paragraph, updating the cross-plugin pointer to cowork-sync accordingly. -->
