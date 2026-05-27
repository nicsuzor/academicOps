# Authoritative Agent × Tool Matrix

Generated on Sat May 16 02:20:43 UTC 2026 from `scripts/audit_agent_compliance.py`.

## Exclusive Tools

| Tool                                      | Intended Owner | Current Users | Status       |
| :---------------------------------------- | :------------- | :------------ | :----------- |
| mcp__plugin_aops-core_pkb__batch_archive  | pauli          | junior        | ❌ Drifted   |
| mcp__plugin_aops-core_pkb__bulk_reparent  | pauli          | junior        | ❌ Drifted   |
| mcp__plugin_aops-core_pkb__merge_node     | pauli          | junior        | ❌ Drifted   |
| mcp__playwright__browser_click            | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_close            | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_console_messages | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_drag             | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_evaluate         | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_file_upload      | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_fill_form        | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_handle_dialog    | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_hover            | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_navigate         | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_navigate_back    | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_network_requests | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_press_key        | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_resize           | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_select_option    | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_snapshot         | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_tabs             | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_take_screenshot  | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_type             | marsha         | marsha        | ✅ Exclusive |
| mcp__playwright__browser_wait_for         | marsha         | marsha        | ✅ Exclusive |
| Edit                                      | rbg            | junior, rbg   | ❌ Drifted   |

## Full Matrix

| Tool                                             | james | junior | marsha | pauli | rbg | enforcer | merge-prep | pr-reviewer | qa  |
| :----------------------------------------------- | :---: | :----: | :----: | :---: | :-: | :------: | :--------: | :---------: | :-: |
| **Built-in**                                     |       |        |        |       |     |          |            |             |     |
| `Agent`                                          |  ✅   |   ✅   |   ✅   |       |     |          |            |             |     |
| `Bash`                                           |  ✅   |   ✅   |   ✅   |  ✅   | ✅  |          |            |             |     |
| `Edit`                                           |       |   ✅   |        |       | ✅  |          |            |             |     |
| `Glob`                                           |       |   ✅   |        |       | ✅  |          |            |             |     |
| `Grep`                                           |       |   ✅   |        |       | ✅  |          |            |             |     |
| `Read`                                           |  ✅   |   ✅   |   ✅   |  ✅   | ✅  |          |            |             |     |
| `Skill`                                          |  ✅   |   ✅   |   ✅   |  ✅   |     |          |            |             |     |
| `Write`                                          |       |   ✅   |        |  ✅   | ✅  |          |            |             |     |
| **aops-core_pkb**                                |       |        |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__append`              |  ✅   |   ✅   |   ✅   |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__batch_archive`       |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__batch_merge`         |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__batch_reclassify`    |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__batch_update`        |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__bulk_reparent`       |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__complete_task`       |  ✅   |   ✅   |        |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__create`              |  ✅   |   ✅   |        |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__create_memory`       |  ✅   |   ✅   |        |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__create_task`         |  ✅   |   ✅   |   ✅   |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__decompose_task`      |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__delete_memory`       |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__find_duplicates`     |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__get_dependency_tree` |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__get_document`        |  ✅   |   ✅   |        |  ✅   | ✅  |          |            |             |     |
| `mcp__plugin_aops-core_pkb__get_network_metrics` |  ✅   |   ✅   |   ✅   |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__get_task`            |  ✅   |   ✅   |   ✅   |  ✅   | ✅  |          |            |             |     |
| `mcp__plugin_aops-core_pkb__get_task_children`   |       |   ✅   |   ✅   |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__graph_stats`         |  ✅   |   ✅   |        |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__list_documents`      |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__list_memories`       |  ✅   |   ✅   |        |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__list_tasks`          |  ✅   |   ✅   |   ✅   |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__merge_node`          |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__pkb_context`         |  ✅   |   ✅   |        |  ✅   | ✅  |          |            |             |     |
| `mcp__plugin_aops-core_pkb__pkb_orphans`         |       |   ✅   |   ✅   |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__pkb_trace`           |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__retrieve_memory`     |  ✅   |   ✅   |        |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__search`              |  ✅   |   ✅   |   ✅   |  ✅   | ✅  |          |            |             |     |
| `mcp__plugin_aops-core_pkb__search_by_tag`       |       |   ✅   |        |       |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__task_search`         |  ✅   |   ✅   |   ✅   |  ✅   |     |          |            |             |     |
| `mcp__plugin_aops-core_pkb__update_task`         |  ✅   |   ✅   |   ✅   |  ✅   |     |          |            |             |     |
| **playwright**                                   |       |        |        |       |     |          |            |             |     |
| `mcp__playwright__browser_click`                 |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_close`                 |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_console_messages`      |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_drag`                  |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_evaluate`              |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_file_upload`           |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_fill_form`             |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_handle_dialog`         |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_hover`                 |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_navigate`              |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_navigate_back`         |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_network_requests`      |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_press_key`             |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_resize`                |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_select_option`         |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_snapshot`              |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_tabs`                  |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_take_screenshot`       |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_type`                  |       |        |   ✅   |       |     |          |            |             |     |
| `mcp__playwright__browser_wait_for`              |       |        |   ✅   |       |     |          |            |             |     |
