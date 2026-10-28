---
title: Prompt Hydration
status: ready
---

# Prompt Hydration

Prompt hydration searches the PKB with each user prompt, incoming channel message, peer report, subagent handback, and task notification and puts the results in front of the agent before it acts, so every turn starts grounded in what the user already knows and has decided. It serves the user, whose prompts arrive with their context attached, and the operator, who configures where the PKB lives and how the search authenticates.

## User stories

### US-1 Grounded prompts and incoming messages

As a user, I want each prompt I type, incoming channel message, peer report, subagent handback, and task notification searched against my PKB, so that the agent starts from prior knowledge and decisions without my asking.

- **AC-1.1** Given a reachable, authorised PKB endpoint, when a prompt or incoming message is submitted, then the agent's turn receives the matching PKB results as advisory context, marked as PKB search results.
- **AC-1.2** Given a prompt wrapped in a channel envelope (such as Telegram) or an agent/peer envelope (such as `<cross-session-message>`, `<teammate-message>`, `<task-notification>`, `<subagent-handback>`, `<agent-message>`, `<handback>`), when it is submitted, then the search query is the text inside the envelope, not the envelope.
- **AC-1.3** Given a prompt longer than 8 KB (8,192 characters), when it is submitted, then the search query is capped at 8 KB (8,192 characters); prompts up to 8 KB are sent whole without 200-character truncation.
- **AC-1.4** Given a search whose results exceed 8,000 characters, when they are injected, then the injected text is cut to 8,000 characters and marked as truncated.
- **AC-1.5** Given a search with no matches or empty content, when the prompt is submitted, then nothing is injected.
- **AC-1.6** Given an agy invocation, whose hook payload carries no prompt, when the turn's first model invocation starts (`invocationNum` 0), then the search query is the text inside `<USER_REQUEST>` of the transcript's latest `USER_INPUT` step (the whole step content when the tags are absent).
- **AC-1.7** Given an agy turn, when a later model invocation in the same turn starts (`invocationNum` above 0), then no search runs.
- **AC-1.8** Given a slash command prompt (`/cmd <arg>`), when it is submitted, then the search query is the `<arg>` text whole up to 8 KB.
- **AC-1.9** Given a PKB search request over MCP, when the call is made, then `arguments` carries `_session` containing `session_id`, `prompt_id`, `agent_id`, `caller: "hook"`, and `surface`, with `prompt_id` matching the turn hook span.

### US-2 Argument-less slash commands make no search calls

As a user, I want argument-less slash commands to make no PKB search calls, so that routine session lifecycle actions and commands do not trigger unnecessary network traffic.

- **AC-2.1** Given an argument-less slash command (`/cmd`), when it is submitted, then no search runs and nothing is injected.

### US-3 Authenticated search from environment and client configuration

As an operator, I want the search to reach an access-controlled PKB endpoint using credentials I set in the environment or client configuration, so that the PKB stays private, sessions authenticate across crew containers and local hosts, and no credential ships in the plugin.

- **AC-3.1** Given `PKB_MCP_URL` and a credential in the hook's environment, when a prompt is submitted, then the search request carries that credential and the endpoint returns results.
- **AC-3.2** Given `PKB_MCP_URL` is unset, when a prompt is submitted, then no search runs and the turn proceeds.
- **AC-3.3** Given credentials are unset in the process environment, when client MCP configuration files (`~/.claude/.claude.json`, `~/.claude.json`, or `~/.gemini/config/mcp_config.json`) contain `services` or `pkb` headers, then the search reads those headers so crew containers and local host sessions authenticate reliably.

### US-4 Failures are visible and name their cause

As an operator, I want a failed search reported to the agent with the reason the endpoint gave, so that I can tell a missing credential from a dead server without re-running the hook by hand.

- **AC-4.1** Given the endpoint rejects the request for want of a valid credential (HTTP 401 or 403), when a prompt is submitted, then the turn proceeds and the injected message says the PKB endpoint refused authorisation and names the credential variables the hook reads.
- **AC-4.2** Given the endpoint is unreachable or does not answer within 5 seconds, when a prompt is submitted, then the turn proceeds and the injected message says so.
- **AC-4.3** Given any failed search, when the turn proceeds, then no other search route is tried.

## Design

**Trigger.** Hydration runs on incoming channel messages and every user prompt submission (`UserPromptSubmit`, never on a `/pull` tool call), before the agent's turn. On agy the trigger is `PreInvocation`, whose payload names the transcript but carries no prompt, so the hook reads the user's text from the transcript's latest `USER_INPUT` step (AC-1.6), skipping harness injections (such as SessionStart system messages) that precede model invocation. When a turn is woken by an incoming peer report or subagent handback via `SYSTEM_MESSAGE`, that arrival is searched. Argument-less slash commands (`/cmd`) are gated out, making no PKB call; human prompts wrapped in `<channel>` envelopes, peer reports, subagent handbacks, task notifications, and `/cmd <arg>` prompts are unwrapped and searched whole up to 8 KB without 200-character truncation.

**Endpoint.** The PKB is an MCP server at `PKB_MCP_URL`, reached via a single streamable-HTTP POST to PKB_MCP_URL. The hook calls its search tool (prefixed by `PKB_MCP_TOOL_PREFIX`, default `pkb_search`) with the query. If the endpoint requires an MCP session, the hook falls back to `initialize` once and caches the session ID for 24 hours in the tracer state dir. Requests carry `x-session-id`, `traceparent` from the active turn, a non-urllib `User-Agent`, and any resolved credential headers (unauthenticated when unset so the cloud proxy injects them). Tool call arguments carry the query and a reserved `_session` attribution object (`session_id`, `prompt_id`, `agent_id`, `caller: "hook"`, `surface`), with `prompt_id` matching the turn hook span (AC-1.9). That is the only transport: a search that fails reports its failure and stops (AC-4.3), because a quiet second route hides the fault that needs fixing.

**Credentials.** The endpoint sits behind an access-controlled gateway, so every request carries a credential. The hook reads credentials from its process environment first (`PKB_MCP_HEADERS`, `WORKER_MCP_TOKEN_*`, `DISPATCHER_MCP_TOKEN_*`, or `CF_ACCESS_CLIENT_*`), and when unset falls back to reading headers from the client's own MCP configuration files (`~/.claude/.claude.json`, `~/.claude.json`, `~/.gemini/config/mcp_config.json`) so crew containers and local host sessions authenticate without duplicate environment variable exports:

| Source | Contents | Sent as |
| - | - | - |
| `PKB_MCP_HEADERS` | JSON object of header name to value, e.g. `{"Authorization": "Bearer <token>"}` | Each pair as an HTTP header. Malformed JSON is logged and ignored. |
| `WORKER_MCP_TOKEN_ID` + `WORKER_MCP_TOKEN_SECRET`, else `DISPATCHER_MCP_TOKEN_ID` + `DISPATCHER_MCP_TOKEN_SECRET`, else `CF_ACCESS_CLIENT_ID` + `CF_ACCESS_CLIENT_SECRET` | A Cloudflare Access service token, both halves. The worker pair is the default because it has no polecat dispatch access. | `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers |
| Client MCP configuration (`~/.claude/.claude.json`, `~/.gemini/config/mcp_config.json`) | `mcpServers.services.headers` or `mcpServers.pkb.headers` | Configured headers (e.g. `CF-Access-Client-Id` / `CF-Access-Client-Secret`) |

**Budget.** The connect-and-search is bounded at 5 seconds, because the hook runs synchronously ahead of every turn. Search queries are capped at 8 KB (8,192 characters). Injected output is capped at 8,000 characters (AC-1.4).

**Output.** Results are injected as advisory context inside `<academicOps PKB search results>` tags. When the server returns no matches or empty content, nothing is injected (AC-1.5). A failure is injected as a single-line message beginning `aops hooks: handler 'search_the_pkb' failed with`, carrying the cause (US-4).
