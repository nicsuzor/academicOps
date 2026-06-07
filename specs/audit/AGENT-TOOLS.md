# Authoritative Agent × Tool Matrix

Generated on Sun Jun 7 00:29:09 UTC 2026 from `scripts/audit_agent_compliance.py`.

## Exclusive Tools

| Tool                                      | Intended Owner | Current Users | Status       |
| :---------------------------------------- | :------------- | :------------ | :----------- |
| mcp__plugin_aops-core_pkb__batch_archive  | pauli          |               | ⚠️ Unused     |
| mcp__plugin_aops-core_pkb__batch_reparent | pauli          |               | ⚠️ Unused     |
| mcp__plugin_aops-core_pkb__merge_node     | pauli          |               | ⚠️ Unused     |
| mcp__playwright__*                        | marsha         | marsha        | ✅ Exclusive |
| Edit                                      | rbg            | junior, rbg   | ❌ Drifted   |

## Full Matrix

| Tool                                             | james | junior | marsha | pauli | rbg | enforcer | merge-prep | pr-reviewer | qa  |
| :----------------------------------------------- | :---: | :----: | :----: | :---: | :-: | :------: | :--------: | :---------: | :-: |
| **Built-in**                                     |       |        |        |       |     |          |            |             |     |
| `Agent`                                          |  ✅   |   ✅   |   ✅   |       |     |          |            |             |     |
| `AskUserQuestion`                                |       |   ✅   |        |       |     |          |            |             |     |
| `Bash`                                           |  ✅   |   ✅   |   ✅   |  ✅   | ✅  |          |            |             |     |
| `Edit`                                           |       |   ✅   |        |       | ✅  |          |            |             |     |
| `Glob`                                           |       |   ✅   |        |       | ✅  |          |            |             |     |
| `Grep`                                           |       |   ✅   |        |       | ✅  |          |            |             |     |
| `Read`                                           |  ✅   |   ✅   |   ✅   |  ✅   | ✅  |          |            |             |     |
| `Skill`                                          |  ✅   |   ✅   |   ✅   |  ✅   |     |          |            |             |     |
| `Write`                                          |       |   ✅   |        |  ✅   | ✅  |          |            |             |     |
| **aops-core_pkb**                                |       |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__*`                   |       |   ✅   |   ✅   |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__append`              |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__complete_task`       |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__create`              |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__create_memory`       |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__create_task`         |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__get_document`        |  ✅   |        |        |       | ✅  |          |            |             |     |
| `mcp__plugin_aops-core_pkb__get_network_metrics` |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__get_task`            |  ✅   |        |        |       | ✅  |          |            |             |     |
| `mcp__plugin_aops-core_pkb__graph_stats`         |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__list_memories`       |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__list_tasks`          |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__pkb_context`         |  ✅   |        |        |       | ✅  |          |            |             |     |
| `mcp__plugin_aops-core_pkb__retrieve_memory`     |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__search`              |  ✅   |        |        |       | ✅  |          |            |             |     |
| `mcp__plugin_aops-core_pkb__task_search`         |  ✅   |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__update_task`         |  ✅   |        |        |       |     |          |            |             |     |
| **outlook**                                      |       |        |        |       |     |          |            |             |     |
| `mcp__outlook__*`                                |       |   ✅   |        |  ✅   |     |          |            |             |     |
| **playwright**                                   |       |        |        |       |     |          |            |             |     |
| `mcp__playwright__*`                             |       |        |   ✅   |       |     |          |            |             |     |
