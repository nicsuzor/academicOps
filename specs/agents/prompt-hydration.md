---
title: Prompt Hydration
type: spec
status: proposed
tier: core
depends_on: []
tags: [framework, routing, context]
---

# Prompt Hydration

Prompt hydration automatically searches the PKB on user input to ground agent turns in authoritative context before execution begins.

## When it runs

The `search_the_pkb` hook handler runs on `UserPromptSubmit` (`plugins/ida/hooks/handlers.py`). This grounds freeform prompts in the PKB without requiring explicit slash commands or manual search invocations.

### Message Origin Filtering

Hydration is restricted strictly to user prompts:

- **Interactive Console Inputs:** Plain text prompts submitted by the user are searched directly.
- **Channel Inputs (Telegram):** Prompts that begin with a `<channel source="..." user="...">...</channel>` envelope are unwrapped by `extract_prompt_query()`; a typed prompt that merely mentions such a tag is searched as typed. The inner user text is stripped of ANSI escape sequences and whitespace, with the first 200 characters sent as the search query.
- **Peer Agent Reports:** Prompts beginning with peer envelopes (`<cross-session-message`, `<teammate-message`, `<task-notification`) are explicitly skipped. Peer reports are claims to be checked under the premise-check gate, not user requests to be grounded in PKB search results.

### Transport and Authentication

Search queries are dispatched to the PKB endpoint (`PKB_MCP_URL`):

- **Header Resolution:** `_resolve_mcp_headers()` resolves authentication headers from the process environment and the session's client configuration:
  - _Environment:_ `PKB_MCP_HEADERS` (a JSON object) and the Cloudflare Access pair `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET`. A malformed `PKB_MCP_HEADERS` is logged and ignored.
  - _Session Client Configurations:_ When environment variables do not supply credentials, the hook inspects the session's client MCP configs for the `services` MCP server entry (or any server matching `PKB_MCP_URL`):
    - Claude Code: `$CLAUDE_CONFIG_DIR/.claude.json`, `~/.claude.json`, `~/.claude/.claude.json`.
    - Antigravity (`agy`): `~/.gemini/config/mcp_config.json`, `~/.gemini/antigravity-cli/mcp_config.json`, `~/.gemini/antigravity-cli/settings.json`.
    Headers defined in the environment take precedence over client config files.
- **In-Process HTTP Search:** The query runs in-process via `fastmcp.Client` over `StreamableHttpTransport` with the resolved headers (or empty headers if none are found), calling `pkb_search`. Connect and call together are bounded by `_SEARCH_TIMEOUT_SECONDS` (5 seconds). The hook does not test an assumed precondition on headers. Any HTTP, network, authentication, or transport error from the endpoint surfaces as a loud hook failure; there is no unauthenticated CLI retry or fallback transport.
- **Injection Budget:** Output is bounded by `_MAX_INJECT_CHARS` (8000 characters) and injected as advisory context inside `<academicOps PKB search results>` XML tags.

