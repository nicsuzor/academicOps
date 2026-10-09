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

- **Header Resolution:** `_resolve_mcp_headers()` reads request headers from the hook's environment only: `PKB_MCP_HEADERS` (a JSON object) and the Cloudflare Access pair `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET`. It never reads a client's own config file. A malformed `PKB_MCP_HEADERS` is logged and ignored.
- **Authenticated search:** When headers are present, the query runs in-process via `fastmcp.Client` over `StreamableHttpTransport`, calling `pkb_search`. Connect and call together are bounded by `_SEARCH_TIMEOUT_SECONDS` (5 seconds). A failure is logged and the turn proceeds without hydration; there is no second transport.
- **Unauthenticated search:** When no headers are configured, the hook invokes the `fastmcp` or `mcp` CLI via `subprocess.run`, with the same timeout.
- **Injection Budget:** Output is bounded by `_MAX_INJECT_CHARS` (8000 characters) and injected as advisory context inside `<academicOps PKB search results>` XML tags.
