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
- **Channel Inputs (Telegram):** Prompts arriving via external channels wrapped in `<channel source="..." user="...">...</channel>` envelopes are unwrapped by `extract_prompt_query()`. The inner user text is stripped of ANSI escape sequences and whitespace, with the first 200 characters sent as the search query.
- **Peer Agent Reports:** Prompts beginning with peer envelopes (`<cross-session-message`, `<teammate-message`, `<task-notification`) are explicitly skipped. Peer reports are claims to be checked under the premise-check gate, not user requests to be grounded in PKB search results.

### Transport and Authentication

Search queries are dispatched to the PKB endpoint (`PKB_MCP_URL`):
- **Header Resolution:** `_resolve_mcp_headers()` retrieves authentication credentials (e.g. Cloudflare Access tokens `CF-Access-Client-Id` and `CF-Access-Client-Secret`) from `PKB_MCP_HEADERS`, environment variables, or `~/.claude.json` (`mcpServers.services.headers`).
- **FastMCP Client:** When authentication headers are present, the query executes asynchronously via `fastmcp.Client` and `StreamableHttpTransport` calling `pkb_search` (or `pkb__search`), bounded by `_SEARCH_TIMEOUT_SECONDS` (5 seconds).
- **Subprocess CLI Fallback:** When custom headers are not configured, calls fall back to invoking `fastmcp` or `mcp` via `subprocess.run`.
- **Injection Budget:** Output is bounded by `_MAX_INJECT_CHARS` (8000 characters) and injected as advisory context inside `<academicOps PKB search results>` XML tags.

