# Authoritative Agent × Tool Matrix

Generated on Wed Jul 1 08:18:13 AM UTC 2026 from `scripts/audit_agent_compliance.py`.

## Exclusive Tools

<!-- markdownlint-disable MD060 -->

| Tool                                      | Intended Owner | Current Users | Status       |
| :---------------------------------------- | :------------- | :------------ | :----------- |
| mcp__plugin_aops-core_pkb__batch_archive  | pauli          |               | ⚠️ Unused     |
| mcp__plugin_aops-core_pkb__batch_reparent | pauli          |               | ⚠️ Unused     |
| mcp__plugin_aops-core_pkb__merge_node     | pauli          |               | ⚠️ Unused     |
| mcp__playwright__*                        | marsha         | marsha        | ✅ Exclusive |
| Edit                                      | rbg            | ida, rbg      | ❌ Drifted   |

## Full Matrix

| Tool                                                | ida | james | marsha | pauli | rbg | enforcer | mechanic | pr-reviewer | pre-admission-responder | qa  |
| :-------------------------------------------------- | :-: | :---: | :----: | :---: | :-: | :------: | :------: | :---------: | :---------------------: | :-: |
| **Built-in**                                        |     |       |        |       |     |          |          |             |                         |     |
| `Agent`                                             | ✅  |  ✅   |   ✅   |       |     |          |          |             |                         |     |
| `AskUserQuestion`                                   | ✅  |       |        |       |     |          |          |             |                         |     |
| `Bash`                                              | ✅  |       |   ✅   |  ✅   | ✅  |          |          |             |                         |     |
| `Edit`                                              | ✅  |       |        |       | ✅  |          |          |             |                         |     |
| `Glob`                                              | ✅  |       |        |       | ✅  |          |          |             |                         |     |
| `Grep`                                              | ✅  |       |        |       | ✅  |          |          |             |                         |     |
| `Read`                                              | ✅  |  ✅   |   ✅   |  ✅   | ✅  |          |          |             |                         |     |
| `Skill`                                             | ✅  |  ✅   |   ✅   |  ✅   |     |          |          |             |                         |     |
| `Write`                                             | ✅  |       |        |  ✅   | ✅  |          |          |             |                         |     |
| **aops-core_pkb**                                   |     |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__*`                      |     |  ✅   |        |  ✅   |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__append`                 | ✅  |       |   ✅   |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__claim_task`             | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__complete_task`          | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__create_memory`          | ✅  |       |   ✅   |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__create_task`            | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__find_duplicates`        | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__get_dependency_tree`    | ✅  |       |   ✅   |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__get_document`           | ✅  |       |   ✅   |       | ✅  |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__get_network_metrics`    | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__get_semantic_neighbors` | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__get_task`               | ✅  |       |   ✅   |       | ✅  |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__get_task_children`      | ✅  |       |   ✅   |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__graph_stats`            | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__list_documents`         | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__list_memories`          | ✅  |       |   ✅   |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__list_tasks`             | ✅  |       |   ✅   |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__pkb_context`            | ✅  |       |   ✅   |       | ✅  |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__pkb_orphans`            | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__pkb_trace`              | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__release_task`           | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__retrieve_memory`        | ✅  |       |   ✅   |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__search`                 | ✅  |       |   ✅   |       | ✅  |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__status`                 | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__task_search`            | ✅  |       |   ✅   |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__task_summary`           | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__top_n_by_metric`        | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__update_body`            | ✅  |       |        |       |     |          |          |             |                         |     |
| `mcp__plugin_aops-core_pkb__update_task`            | ✅  |       |        |       |     |          |          |             |                         |     |
| **outlook**                                         |     |       |        |       |     |          |          |             |                         |     |
| `mcp__outlook__*`                                   | ✅  |       |        |  ✅   |     |          |          |             |                         |     |
| **playwright**                                      |     |       |        |       |     |          |          |             |                         |     |
| `mcp__playwright__*`                                |     |       |   ✅   |       |     |          |          |             |                         |     |
| **zot**                                             |     |       |        |       |     |          |          |             |                         |     |
| `mcp__zot__*`                                       | ✅  |       |        |       |     |          |          |             |                         |     |

<!-- markdownlint-enable MD060 -->
