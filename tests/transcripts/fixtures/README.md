# Transcript Test Fixtures

This directory contains real, anonymized transcript fixtures used for testing the session transcript pipelines.

## Fixture Details

### `claude_session.jsonl`

- **Provenance**: Extracted from a real Claude Code session on the host machine (from a pre-dispatch safety check task).
- **Anonymization**:
  - User name and home paths redacted to `/home/<user>`.
  - Tailscale internal URL replaced with `services.mcp.local`.
  - Hostname replaced with `<machine>`.
  - Sensitive token lengths/endings preserved in original shape but verified to not contain actual usable secrets.

### `agy_session.jsonl`

- **Provenance**: Extracted from a real agy session (specifically the initial steps of the current active session executing under `epic_XXXXXXXX`).
- **Anonymization**:
  - Raw PKB epic and task IDs masked (e.g., `epic_XXXXXXXX`, `aops_XXXXXXXX`, `task-XX`).
  - Conversation ID masked to `conversation_XXXXXXXX`.
  - Task and parent task titles redacted to `[REDACTED_TITLE]`, `[REDACTED_PARENT_TITLE]`, etc.
  - User names, paths, internal domain URLs, and machine names replaced with generic placeholders (`<user>`, `<machine>`, `services.mcp.local`).

### `claude_session.snapshot.md` / `claude_session.snapshot.json`

- **Provenance**: Golden rendered output committed by the Claude adapter's snapshot tests (`tests/transcripts/test_claude_adapter.py`), generated from `claude_session.jsonl` via `aops/lib/transcripts/adapters/claude.py` (which wraps the live `claude-code-log` library).
- **Purpose**: Any upstream `claude-code-log` change that alters rendered output shows up as a diffable CI failure here instead of a silent production drift. Derived entirely from the already-anonymized fixture above — no new sensitive content.
- **Regenerating after an intentional change**: re-run the render calls in `test_markdown_snapshot`/`test_json_snapshot`, review the diff, and overwrite these files.

## Sensitivity and Integrity Assurance

All files in this directory have been manually checked for sensitivity before commit, ensuring they contain zero private credentials, personal names, or exact internal task metadata, while strictly preserving the JSONL schema and shape of their respective sources.
