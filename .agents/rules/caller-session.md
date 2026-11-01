---
trigger: always_on
description: Ensure non-hook clients supply caller session context on MCP tool calls targeting session-aware servers.
---

## Supply caller session on MCP tool calls

Calls to MCP servers that consume caller session (`pkb`, `services`) must carry the caller's session identity so upstream services can correlate operations with the calling session.

Clients that do not mechanically inject session context (such as the Antigravity `agy` client) must explicitly include the reserved `_session` argument object when calling tools on servers that consume caller session (`pkb`, `services`), containing `session_id` set to the session ID / conversation ID learned at session start (e.g. the Conversation ID from session context), along with `agent_id` and `prompt_id` when known. Calls to other MCP servers must not include `_session`.
