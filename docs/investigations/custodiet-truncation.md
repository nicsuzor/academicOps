# Investigation: Custodiet Context Truncation After Compaction

## Overview

This investigation aimed to identify why the custodiet context file appears truncated or loses information after a session has been compacted (context window compression).

## Findings

### 1. Context Generation Mechanism

- **Code Responsible**: `aops-core/lib/gates/custom_actions.py:create_audit_file`
- **Core Logic**: `aops-core/lib/session_reader.py:build_audit_session_context`
- **Hook Trigger**: The `custodiet` gate triggers on the `PreToolUse` hook event when `ops_since_open >= CUSTODIET_TOOL_CALL_THRESHOLD`.
- **Action**: When the threshold is reached, `prepare_compliance_report` calls `create_audit_file`, which uses `build_audit_session_context` to generate a chronological narrative of the session and writes it to a `*-custodiet.md` file.

### 2. Truncation and Data Loss Causes

#### A. Missing Compaction Summaries (Root Cause for "After Compaction")

In `aops-core/lib/session_reader.py`, the `build_audit_session_context` function explicitly filters out `summary` type turns:

```python
# Filter out non-conversation and meta-only turns first to get a clean list
valid_turns = []
for turn in turns:
    turn_type = turn.get("type") if isinstance(turn, dict) else None
    if turn_type in ("hook_context", "summary"):
        continue
    ...
```

Claude Code compaction produces a `summary` entry in the session JSONL. By skipping this entry, the auditor loses the entire high-level history of everything that was compacted.

#### B. Detailed Turn Limit

The auditor narrative is split into "Historical User Intent" and "Recent Activity":

- `_DETAILED_TURNS_LIMIT = 5`: Only the **last 5 turns** include agent reasoning, tool calls, and results.
- **Older turns**: Only the **user message** is preserved. Agent reasoning and tool operations are discarded for everything older than the 5-turn detailed window.

#### C. Character Limits per Turn

Even for detailed turns, strict truncation limits apply:

- `_AGENT_TEXT_LIMIT = 2000`: Agent reasoning is capped at 2000 characters.
- `_TOOL_ARG_LIMIT = 300`: Tool arguments are capped at 300 characters.
- `_TOOL_RESULT_LIMIT = 1000`: Tool results (e.g., Bash output) are capped at 1000 characters.

### 3. Compaction and Regeneration

- **Compaction Event**: The `PreCompact` hook is defined in `hooks.json` and mapped in `router.py`, but it does **not** trigger a custodiet reset or regeneration in `definitions.py`.
- **Regeneration**: Regeneration happens on the **first tool call after compaction** that triggers the custodiet gate. Because the JSONL now contains a `summary` entry (which is skipped) and fewer historical entries, the resulting `*-custodiet.md` file is significantly shorter and missing the compacted history.

### 4. Race Conditions

- **Observation**: Multiple concurrent tool calls could theoretically invoke the hook router simultaneously.
- **Mitigation**:
  - `router.py` loads and saves `SessionState` atomically.
  - `create_audit_file` writes to a predictable path using `Path.write_text()`.
  - Most Claude Code tool executions are sequential, reducing the likelihood of concurrent hook router execution for the same session.
  - However, if two processes trigger `create_audit_file` at once, one might overwrite the other's work, but the content should be identical if based on the same JSONL state.

## Conclusion

The "truncation after compaction" is primarily caused by `build_audit_session_context` ignoring `summary` entries in the session JSONL and its aggressive truncation of historical turns (only preserving user prompts for anything older than 5 turns).

## Recommendations

1. **Modify `build_audit_session_context`** to include `summary` type turns in the auditor narrative.
2. **Increase `_DETAILED_TURNS_LIMIT`** or provide a more graceful degradation for historical turns (e.g., including tool names without results).
3. **Handle `PreCompact`** in `definitions.py` if proactive regeneration is desired, though fixing the reader is likely sufficient.
