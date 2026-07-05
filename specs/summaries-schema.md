---
type: spec
title: Session Summaries Metrics Schema
status: ready
tier: 4
tags: [framework, schema, summaries, metrics, transcript]
---

# Session Summaries Metrics Schema

Reference schema for session summaries JSON files written by `aops-core/scripts/transcript.py` and validated by `validate_insights_schema` in `aops-core/lib/insights_generator.py`. Files live under `summaries/YYYY-MM/` in the rotated layout.

## How to Query

The framework produces one structured JSON summary per session at:

```
$AOPS_SESSIONS/summaries/YYYY-MM/<session_id>.json
```

**This is the canonical first stop for prompt mining and command-usage analysis.** Use it before touching raw transcript files.

### Primary field — `timeline_events`

Each summary contains a `timeline_events` list of `{timestamp, type, description, system_injected}` objects. Filter to `type == "user_prompt"` to get verbatim user turns. `initial_prompt` captures turn 1 only — most command invocations (e.g. `/learn`) happen mid-session and are only visible via `timeline_events`.

**Two equivalent paths to genuine human prompts — pick one:**

1. **Read the top-level `user_prompts` array** — `[{timestamp, text}]`, pre-filtered to `system_injected=false` and secrets-redacted at write time. Simplest path for most use cases.
2. **Filter `timeline_events`** to `type == "user_prompt"` AND `system_injected == false`. Works across ALL clients (polecat, sdk, claude-code, claude-desktop) — do **not** filter by client name, as that drops genuine human `/learn` invocations inside polecat/sdk sessions.

`system_injected=true` marks machine-authored turns (task-notification, loaded_context, polecat worker dispatch, skill bodies) using purely syntactic prefix matching — no NLP.

### Other useful fields

| Field                                                                    | Description                                                        |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `user_prompts`                                                           | `[{timestamp, text}]` — pre-filtered genuine human turns, redacted |
| `initial_prompt`                                                         | First user turn only (misses mid-session invocations)              |
| `user_prompt_count`                                                      | Count of genuine user turns (`system_injected=false`)              |
| `client`                                                                 | e.g. `claude-code`, `claude-desktop`, `polecat`, `sdk`             |
| `surface`                                                                | e.g. `interactive`, `polecat`, `gha`                               |
| `session_type`                                                           | Session type classifier                                            |
| `summary`, `accomplishments`, `friction_points`, `framework_reflections` | Session narrative fields                                           |
| `task_id`                                                                | Associated task, if any                                            |

### When to use vs raw transcripts

| Task                                                              | Source                                                     |
| ----------------------------------------------------------------- | ---------------------------------------------------------- |
| Mine what the user typed — prompts, `/command` invocations        | **Summaries JSON** (`timeline_events[type="user_prompt"]`) |
| Count command usage or extract patterns from user turns           | **Summaries JSON** first                                   |
| Derive structured understanding of sessions (trends, topics)      | **Summaries JSON** first                                   |
| Extract agent reasoning, tool calls, or full conversation context | Raw transcripts (`$AOPS_SESSIONS/transcripts/YYYY-MM/`)    |
| Summaries JSON absent or insufficient for the task                | Raw transcripts as **fallback only**                       |

**Raw transcripts are the last-resort fallback.** `$AOPS_SESSIONS/transcripts/YYYY-MM/*-{abridged,full}.md` (~5–6k files/month). Naïve `grep -r` hits thousands of files (incidental agent mentions, skill bodies, injected task-notifications) and requires parsing multiple user-turn marker formats — expensive and error-prone.

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

| Field                       | Type           | Description                                                                                      |
| --------------------------- | -------------- | ------------------------------------------------------------------------------------------------ |
| `friction_points`           | array[string]  | Obstacles or blockers encountered                                                                |
| `proposed_changes`          | array[string]  | Follow-up actions or improvements                                                                |
| `workflows_used`            | array[string]  | Framework workflows invoked                                                                      |
| `subagents_invoked`         | array[string]  | Subagent identifiers spawned                                                                     |
| `learning_observations`     | array[string]  | Lessons captured                                                                                 |
| `context_gaps`              | array[string]  | Missing context that caused friction                                                             |
| `conversation_flow`         | array          | Structured turn log                                                                              |
| `user_prompts`              | array[object]  | Ordered human-typed prompts `{timestamp, text}` — excludes system-injected turns (aops-519f8e11) |
| `workflow_improvements`     | array[string]  | Suggested workflow changes                                                                       |
| `jit_context_needed`        | array[string]  | JIT context that was absent                                                                      |
| `context_distractions`      | array[string]  | Irrelevant context loaded                                                                        |
| `framework_reflections`     | array[object]  | Structured per-reflection entries (see below)                                                    |
| `timeline_events`           | array[object]  | Ordered session events for path reconstruction                                                   |
| `token_metrics`             | object         | Token usage breakdown (see section below)                                                        |
| `subagent_count`            | int            | Number of subagents spawned                                                                      |
| `enforcer_blocks`           | int            | Number of enforcer interventions                                                                 |
| `acceptance_criteria_count` | int            | Acceptance criteria evaluated                                                                    |
| `user_mood`                 | float          | Sentiment proxy, range -1.0 to 1.0                                                               |
| `user_prompt_count`         | int or null    | Count of genuine human-typed turns (`system_injected=false`)                                     |
| `current_bead_id`           | string or null | PKB bead/task linked to session                                                                  |
| `worker_name`               | string or null | Agent worker identity                                                                            |
| `task_id`                   | string         | Linked task ID (from `$AOPS_TASK_ID`)                                                            |
| `repo`                      | string         | Alias of `project` for downstream consumers                                                      |
| `pr_url`                    | string         | PR URL if a PR was created this session                                                          |
| `outputs`                   | array          | Declared outputs from reflection                                                                 |
| `output_explicit_none`      | bool           | Whether agent declared no outputs explicitly                                                     |
| `output_none_reason`        | string or null | Reason for no outputs                                                                            |
| `tasks_worked`              | array          | Tasks touched during session                                                                     |
| `references`                | array          | External references cited                                                                        |
| `quality_warnings`          | array          | Quality-bar flags from reflection                                                                |
| `thread_pickup`             | object         | Resume context for next session                                                                  |
| `started_at`                | string         | ISO 8601 session start time                                                                      |
| `ended_at`                  | string         | ISO 8601 session end time                                                                        |

### `timeline_events` entry structure

Each entry has at minimum `{timestamp, type}`. The `user_prompt` type also carries:

| Field             | Type    | Description                                                                                                                                                                                                                                                                   |
| ----------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `description`     | string  | Raw prompt text                                                                                                                                                                                                                                                               |
| `system_injected` | boolean | `true` for machine-authored turns (harness envelopes, worker dispatch, skill bodies, loaded context). `false` for human-typed prompts. Mining "what the user typed" = filter `system_injected=false` across all clients with zero hand-written noise regexes (aops-519f8e11). |

`user_prompts` (top-level array) is the pre-filtered view: `[{timestamp, text}]` where each entry is a `user_prompt` event with `system_injected=false`.

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

These fields are populated by **deterministic regex bucketing** in
`parse_framework_reflection`, not by an LLM. The agent's `## Framework Reflection`
block must use the exact bold labels the parser matches, or the structured parse
matches nothing and the body is dumped wholesale into `accomplishments` (the
`aops-6a787364` silent-corruption bug). The full label → field mapping, drift
tolerances, and quality warnings (`inferred-reflection`, `friction-in-accomplishments`)
are the SSoT in `aops-interactive/skills/end_session/transcript-metadata-schema.md`
(moved from `aops-core` — aops-cf3fb2f0; and `SKILL.md`'s reflection template
must stay in lock-step with it).

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

All fields introduced in CC 2.1+ (`attribution`, `stop_reasons`, `thinking_turns`, `git_branches`, `permission_modes`, `session_kind`, `user_type`, `entrypoint`, `client_version`, `token_metrics.totals.server_tool_use`, `token_metrics.totals.service_tier`) are omitted from the JSON when the source data is absent. Consumers must treat these fields as optional. Older summary files (pre-CC 2.1) are fully valid without them.
