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
allowed-tools: Bash,Read,Write,Grep,Glob,Edit,Skill,mcp_pkb_search,mcp_pkb_pkb_orphans,mcp_pkb_create_memory,mcp_pkb_list_tasks,mcp_pkb_graph_stats,mcp_pkb_get_network_metrics,mcp_pkb_update_task,mcp_pkb_get_task,mcp_pkb_task_search,mcp_pkb_pkb_context,mcp_pkb_bulk_reparent,mcp_pkb_find_duplicates,mcp_pkb_batch_merge,mcp_pkb_merge_node,mcp_pkb_complete_task,mcp_pkb_batch_reclassify,mcp_pkb_batch_archive,mcp_pkb_batch_update,mcp_pkb_create_task,mcp_pkb_release_task
owner: pauli
version: 1.0.0
superseded_by: aops-core/skills/remember/SKILL.md
---

# Sleep Skill (Unified into /remember)

This skill has been merged into [[remember]]. For all `/sleep` and consolidation maintenance mode instructions, refer to `aops-core/skills/remember/SKILL.md`.
