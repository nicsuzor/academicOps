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
allowed-tools: Read, Grep, Glob, Skill, mcp__plugin_aops-core_pkb__list_tasks, mcp__plugin_aops-core_pkb__get_task, mcp__plugin_aops-core_pkb__pkb_context, mcp__plugin_aops-core_pkb__graph_json
permalink: commands/maintain
---

# /maintain — Graph Hygiene Audit

Runs graph-hygiene and anti-inflation audits on the task graph. Surface findings only—do not block execution or auto-fix.

## Invocation & Arguments

- `/maintain` — run all hygiene checks against the entire graph.
- `/maintain <project>` — run checks scoped to the specified project.

## Execution Protocol

1. **Delegate**: Invoke the `planner` skill to run the audit:
   `Skill(skill="planner", args="maintain: anti-inflation")`
2. **Fallback**: If the planner skill is unavailable, read the task graph via `mcp__plugin_aops-core_pkb__list_tasks` and check frontmatter properties. Do not perform any write operations.

## Output Format

Report the results using these exact section headings:

### 1. Targets missing `consequence` prose

List target nodes missing `consequence` prose:
`Targets missing consequence prose (SURFACE):`

### 2. `contributes_to` edges missing `why:` / `justification:`

List edges missing justification details:
`contributes_to edges missing justification (SURFACE):`

### 3. SEV4 targets with weak consequence prose (advisory heuristic)

List SEV4 targets with vague or non-concrete consequence text:
`SEV4 targets with weak consequence prose (advisory — heuristic):`

### 4. Active SEV4-committed target concurrency

Count committed targets with severity 4. Cap is 2. If exceeded, output:
`SEV4-committed concurrency exceeded: N active (cap = 2). Review or downgrade.`

### 5. Type/ID-prefix/Filename consistency

List nodes with ID prefix, type, or filename mismatches:
`Type/ID/Filename mismatches (SURFACE):`
