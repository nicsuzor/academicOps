---
type: spec
title: Session Insights Metrics Schema
status: ready
tier: 4
tags: [framework, schema, insights, metrics, transcript]
---

# Session Insights Metrics Schema

Reference schema for session insights JSON files written by `aops-core/scripts/transcript.py` and validated by `validate_insights_schema` in `aops-core/lib/insights_generator.py`. Files live under `summaries/YYYY-MM/` in the rotated layout.

## Required Fields

| Field             | Type          | Constraints                                       | Description                     |
| ----------------- | ------------- | ------------------------------------------------- | ------------------------------- |
| `session_id`      | string        | 8-char hex hash                                   | Unique session identifier       |
| `date`            | string        | ISO 8601 (`YYYY-MM-DD` or full timestamp with tz) | Session date/time               |
| `project`         | string        |                                                   | Repository or project name      |
| `summary`         | string        |                                                   | Human-readable one-line summary |
| `outcome`         | string        | `success`, `partial`, `failure`                   | Session result                  |
| `accomplishments` | array[string] |                                                   | List of completed items         |

## Optional Standard Fields

| Field                       | Type           | Description                                    |
| --------------------------- | -------------- | ---------------------------------------------- |
| `friction_points`           | array[string]  | Obstacles or blockers encountered              |
| `proposed_changes`          | array[string]  | Follow-up actions or improvements              |
| `workflows_used`            | array[string]  | Framework workflows invoked                    |
| `subagents_invoked`         | array[string]  | Subagent identifiers spawned                   |
| `learning_observations`     | array[string]  | Lessons captured                               |
| `context_gaps`              | array[string]  | Missing context that caused friction           |
| `conversation_flow`         | array          | Structured turn log                            |
| `user_prompts`              | array[string]  | Significant user instructions                  |
| `workflow_improvements`     | array[string]  | Suggested workflow changes                     |
| `jit_context_needed`        | array[string]  | JIT context that was absent                    |
| `context_distractions`      | array[string]  | Irrelevant context loaded                      |
| `framework_reflections`     | array[object]  | Structured per-reflection entries (see below)  |
| `timeline_events`           | array[object]  | Ordered session events for path reconstruction |
| `token_metrics`             | object         | Token usage breakdown (see section below)      |
| `subagent_count`            | int            | Number of subagents spawned                    |
| `enforcer_blocks`           | int            | Number of enforcer interventions               |
| `acceptance_criteria_count` | int            | Acceptance criteria evaluated                  |
| `user_mood`                 | float          | Sentiment proxy, range -1.0 to 1.0             |
| `user_prompt_count`         | int or null    | Count of real user-role turns                  |
| `current_bead_id`           | string or null | PKB bead/task linked to session                |
| `worker_name`               | string or null | Agent worker identity                          |
| `task_id`                   | string         | Linked task ID (from `$AOPS_TASK_ID`)          |
| `repo`                      | string         | Alias of `project` for downstream consumers    |
| `pr_url`                    | string         | PR URL if a PR was created this session        |
| `outputs`                   | array          | Declared outputs from reflection               |
| `output_explicit_none`      | bool           | Whether agent declared no outputs explicitly   |
| `output_none_reason`        | string or null | Reason for no outputs                          |
| `tasks_worked`              | array          | Tasks touched during session                   |
| `references`                | array          | External references cited                      |
| `quality_warnings`          | array          | Quality-bar flags from reflection              |
| `thread_pickup`             | object         | Resume context for next session                |
| `started_at`                | string         | ISO 8601 session start time                    |
| `ended_at`                  | string         | ISO 8601 session end time                      |

### `framework_reflections` entry structure

Each entry in the array represents one reflection block:

| Field               | Type           | Description                                |
| ------------------- | -------------- | ------------------------------------------ |
| `prompts`           | string         | Skill/prompt that triggered the reflection |
| `guidance_received` | string or null | Framework guidance surfaced                |
| `followed`          | bool or null   | Whether guidance was followed              |
| `outcome`           | string         | `success`, `partial`, or `failure`         |
| `accomplishments`   | array[string]  | Items completed in this reflection scope   |
| `friction_points`   | array[string]  | Friction in this scope                     |
| `root_cause`        | string or null | Root cause of friction                     |
| `proposed_changes`  | array[string]  | Proposed fixes                             |
| `next_step`         | string or null | Immediate next action                      |
| `quick_exit`        | bool           | (optional) Whether session was cut short   |

## New Fields (CC 2.1+)

These fields are populated when the transcript contains CC 2.1+ metadata entries. All are omitted when absent (see backward compatibility note).

### Session context fields

| Field              | Type          | Example                 | Description                                                          |
| ------------------ | ------------- | ----------------------- | -------------------------------------------------------------------- |
| `session_kind`     | string        | `"bg"`, `"interactive"` | How the session was launched                                         |
| `user_type`        | string        | `"external"`            | User classification from CC metadata                                 |
| `entrypoint`       | string        | `"cli"`                 | How Claude Code was invoked                                          |
| `client_version`   | string        | `"2.1.152"`             | CC client version string                                             |
| `git_branches`     | array[string] | `["main", "feat/x"]`    | All git branches observed during session (plural key, always a list) |
| `permission_modes` | array[string] | `["default"]`           | Permission mode(s) active during session (plural key, always a list) |

### Usage attribution

`attribution` (object) — plugin/skill/MCP usage counts for the session:

```json
{
  "plugins": ["aops-core", "aops-tools"],
  "skills": ["end_session", "pull"],
  "mcp_servers": { "aops-core_pkb": 12, "filesystem": 3 },
  "mcp_tools": { "mcp__plugin_aops-core_pkb__search": 8 }
}
```

| Sub-field     | Type              | Description                               |
| ------------- | ----------------- | ----------------------------------------- |
| `plugins`     | array[string]     | Plugin names seen in attribution metadata |
| `skills`      | array[string]     | Skill names invoked                       |
| `mcp_servers` | object{name: int} | MCP server name to call-count map         |
| `mcp_tools`   | object{name: int} | MCP tool name to call-count map           |

### Stop reasons

`stop_reasons` (object) — map of stop reason to occurrence count:

```json
{ "end_turn": 14, "tool_use": 6, "max_tokens": 1 }
```

Known stop reason keys: `end_turn`, `tool_use`, `max_tokens`, `refusal`. Additional values are passed through as-is.

### Thinking turns

`thinking_turns` (int) — number of assistant turns that contained a `thinking` or `redacted_thinking` content block.

## Gemini-Specific Fields

Present only when the session was a Gemini CLI session. Sourced from a sidecar `*-session.json` file adjacent to the transcript.

| Field               | Type   | Description                                                                     |
| ------------------- | ------ | ------------------------------------------------------------------------------- |
| `session_type`      | string | Gemini session variant (e.g., `"agentic"`)                                      |
| `gemini_version`    | string | Gemini CLI version string                                                       |
| `global_turn_count` | int    | Total turns across the full Gemini session                                      |
| `gates`             | object | Gate state dict from sidecar (keys are gate names, values are gate status)      |
| `main_agent`        | object | `{"todos": {"completed": int, "total": int}}` — todo completion from main agent |

## `token_metrics` Structure

| Sub-object   | Contents                                                            |
| ------------ | ------------------------------------------------------------------- |
| `totals`     | Aggregate token counts for the full session                         |
| `by_model`   | Per-model breakdown: `{model_name: {input: int, output: int, ...}}` |
| `by_tool`    | Per-tool token breakdown                                            |
| `by_agent`   | Per-agent token breakdown                                           |
| `efficiency` | Derived metrics                                                     |
| `attention`  | Human-attention proxies                                             |

### `token_metrics.totals` fields

| Field                 | Type   | New in CC 2.1+ | Description                                           |
| --------------------- | ------ | -------------- | ----------------------------------------------------- |
| `input_tokens`        | int    |                | Total prompt tokens                                   |
| `output_tokens`       | int    |                | Total completion tokens                               |
| `cache_read_tokens`   | int    |                | Tokens read from prompt cache                         |
| `cache_create_tokens` | int    |                | Tokens written to prompt cache                        |
| `server_tool_use`     | int    | Yes            | Server-side tool use token count                      |
| `service_tier`        | string | Yes            | Service tier reported by the API (e.g., `"standard"`) |

### `token_metrics.efficiency` fields

| Field                      | Type  | Constraints | Description                                |
| -------------------------- | ----- | ----------- | ------------------------------------------ |
| `cache_hit_rate`           | float | 0.0–1.0     | Fraction of input tokens served from cache |
| `tokens_per_minute`        | float |             | Session throughput                         |
| `session_duration_minutes` | float |             | Wall-clock session length                  |

## Backward Compatibility

All fields introduced in CC 2.1+ (`attribution`, `stop_reasons`, `thinking_turns`, `git_branches`, `permission_modes`, `session_kind`, `user_type`, `entrypoint`, `client_version`, `token_metrics.totals.server_tool_use`, `token_metrics.totals.service_tier`) are omitted from the JSON when the source data is absent. Consumers must treat these fields as optional. Older insights files (pre-CC 2.1) are fully valid without them.
