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
allowed-tools: Bash,Read,Write,Grep,Glob,Edit,Skill,mcp__pkb__search,mcp__pkb__pkb_orphans,mcp__pkb__create_memory,mcp__pkb__list_tasks,mcp__pkb__graph_stats,mcp__pkb__get_network_metrics,mcp__pkb__update_task,mcp__pkb__get_task,mcp__pkb__task_search,mcp__pkb__pkb_context,mcp__pkb__bulk_reparent,mcp__pkb__find_duplicates,mcp__pkb__batch_merge,mcp__pkb__merge_node,mcp__pkb__complete_task,mcp__pkb__batch_reclassify,mcp__pkb__batch_archive,mcp__pkb__batch_update,mcp__pkb__create_task,mcp__pkb__release_task
owner: pauli
version: 1.0.0
superseded_by: aops-core/skills/remember/SKILL.md
---

# Sleep Skill (Unified into /remember)

This skill has been merged into [[remember]]. For all `/sleep` and consolidation maintenance mode instructions, refer to `aops-core/skills/remember/SKILL.md`.
