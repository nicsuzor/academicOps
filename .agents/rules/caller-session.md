---
trigger: always_on
description: Ensure non-hook clients supply caller session context on MCP tool calls.
---

## Supply caller session on MCP tool calls

Every MCP tool call must carry the caller's session identity so upstream services can correlate operations with the calling session.

Clients that do not mechanically inject session context (such as the Antigravity `agy` client) must explicitly include the reserved `_session` argument object in every MCP call, containing `session_id` set to the session ID learned at session start (e.g. the Conversation ID from session context), along with `agent_id` and `prompt_id` when known.
