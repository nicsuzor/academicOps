---
name: sleep
type: skill
category: operations
description: "Periodic consolidation agent — unified into the /remember skill (maintenance mode). This stub exists for backwards compatibility with installed GHA workflows."
triggers:
  - "sleep cycle"
  - "consolidation"
  - "brain maintenance"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Bash,Read,Write,Grep,Glob,Edit,Skill,mcp__pkb__search,mcp__pkb__pkb_orphans,mcp__pkb__create_memory,mcp__pkb__list_tasks,mcp__pkb__graph_stats,mcp__pkb__get_network_metrics,mcp__pkb__update_task,mcp__pkb__get_task,mcp__pkb__task_search,mcp__pkb__pkb_context,mcp__pkb__bulk_reparent,mcp__pkb__find_duplicates,mcp__pkb__batch_merge,mcp__pkb__merge_node,mcp__pkb__complete_task,mcp__pkb__batch_reclassify,mcp__pkb__batch_archive,mcp__pkb__batch_update,mcp__pkb__create_task
owner: pauli
version: 1.0.0
superseded_by: aops-core/skills/remember/SKILL.md
---

# Sleep Skill (Unified into /remember)

> **This skill has been merged into [[remember]].** The `/sleep` and GHA cron consolidation behaviours are now the **maintenance mode** of the unified memory skill.

## Where to Go

- **Skill overview and values**: `aops-core/skills/remember/SKILL.md` → section "Maintenance Mode"
- **Full phase instructions (0–11)**: `aops-core/skills/remember/references/maintenance-phases.md`
- **Knowledge writing standards**: `aops-core/skills/remember/SKILL.md` → section "Immediate Mode"

## For GHA Workflows

If you are reading this from an installed `sleep-cycle.yml` workflow that references this file, read the unified skill files instead:

```
aops-core/skills/remember/SKILL.md
aops-core/skills/remember/references/maintenance-phases.md
aops-core/skills/remember/procedures/consolidate.md
```

Update your installed workflow to reference `remember/SKILL.md` and `remember/references/maintenance-phases.md` instead of this file. The template at `templates/github-workflows/sleep-cycle.yml` in the academicOps repo has already been updated.

## Behaviour (unchanged)

The maintenance mode of [[remember]] provides identical behaviour to the previous `/sleep` skill. No functionality was removed — the content was reorganised so that both immediate knowledge writes and periodic consolidation share one canonical skill with no duplication.
