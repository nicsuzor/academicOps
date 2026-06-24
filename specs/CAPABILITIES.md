# Framework Capabilities & Artifacts

This document catalogs the operational capabilities, artifacts, and artifact conventions managed by the academicOps framework.

## Transcripts

The framework records every LLM prompt as an individual transcript file, rather than one monolithic transcript per session.

**Naming Convention:**

```text
{date}-{time}-{session_id}-{shortform}-[task-{short_task_id}-]{slug}{-variant}.{ext}
```

- `date`: `YYYYMMDD` format.
- `time`: `HHMM` format.
- `session_id`: 8-character hash identifying the overarching session.
- `shortform`: Identifying context constructed from available identifiers (e.g., crew, repo, and provider like `claude` or `gemini`), joined by hyphens.
- `task_prefix`: Optional `task-XXXXXXXX-` prefix prepended to the slug when the session is associated with a task ID.
- `slug`: A short slug derived from the specific prompt content, making each file unique per interaction within the session.
- `variant`: Usually `-full` or `-abridged` (empty for some artifact types).

### Finding the Current Transcript

Because transcripts are per-prompt, asking to find "the current transcript" requires identifying the most recently modified file for a given `session_id`.

**Recipe to find the most recent full transcript for a session:**

```bash
# Transcripts are sharded into yyyy-mm/ subdirs after rotation; recent ones stay at top level.
find $AOPS_SESSIONS/transcripts -name "*-${session_id}-*-full.md" -printf '%T@ %p\n' | sort -rn | head -n 1 | cut -d' ' -f2-
```

_(Substitute `${session_id}` with your actual 8-character session ID.)_

## Session Summaries (Structured Corpus)

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
| Derive structured insight about sessions (trends, topics)         | **Summaries JSON** first                                   |
| Extract agent reasoning, tool calls, or full conversation context | Raw transcripts (`$AOPS_SESSIONS/transcripts/YYYY-MM/`)    |
| Summaries JSON absent or insufficient for the task                | Raw transcripts as **fallback only**                       |

**Raw transcripts are the last-resort fallback.** `$AOPS_SESSIONS/transcripts/YYYY-MM/*-{abridged,full}.md` (~5–6k files/month). Naïve `grep -r` hits thousands of files (incidental agent mentions, skill bodies, injected task-notifications) and requires parsing multiple user-turn marker formats — expensive and error-prone.
