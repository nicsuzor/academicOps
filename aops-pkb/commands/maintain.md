---
name: maintain
type: command
category: instruction
description: Surface (don't block) target/prototype graph hygiene issues — missing consequence prose, edges without `why:`, SEV4 weak-prose flags.
triggers:
  - "maintain"
  - "graph hygiene"
  - "anti-inflation"
  - "target hygiene"
  - "consequence audit"
modifies_files: false
needs_task: false
mode: execution
domain:
  - operations
  - planning
allowed-tools: Skill
permalink: commands/maintain
---

# /maintain — Graph Hygiene Audit

Runs graph-hygiene and anti-inflation audits on the task graph. Surface findings only—do not block execution or auto-fix.

## Execution Protocol

Invoke the `planner` skill to run the audit:
`Skill(skill="planner", args="maintain: anti-inflation")`
