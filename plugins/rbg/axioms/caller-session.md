---
description: Ensure every MCP call carries the caller session identity for cross-surface correlation.
trigger: always_on
---

## Caller Session

Every MCP tool call must carry the caller's session identity so upstream services can correlate operations with the calling session.

Clients that do not mechanically inject session context (such as the Antigravity `agy` client) must explicitly include the reserved `_session` argument object in every MCP call, containing `session_id` set to the session ID learned at session start (e.g. the Conversation ID from session context), along with `agent_id` and `prompt_id` when known.
