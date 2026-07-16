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
- **Provenance**: Extracted from a real agy session (specifically the initial steps of the current active session executing under `epic_912eec6e`).
- **Anonymization**:
  - Raw PKB epic and task IDs masked (e.g., `epic_XXXXXXXX`, `aops_XXXXXXXX`, `task-XX`).
  - Conversation ID masked to `conversation_XXXXXXXX`.
  - Task and parent task titles redacted to `[REDACTED_TITLE]`, `[REDACTED_PARENT_TITLE]`, etc.
  - User names, paths, internal domain URLs, and machine names replaced with generic placeholders (`<user>`, `<machine>`, `services.mcp.local`).

## Sensitivity and Integrity Assurance
All files in this directory have been manually checked for sensitivity before commit, ensuring they contain zero private credentials, personal names, or exact internal task metadata, while strictly preserving the JSONL schema and shape of their respective sources.
