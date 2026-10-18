---
title: Prompt Hydration
status: ready
---

# Prompt Hydration

Prompt hydration searches the PKB with each user prompt and puts the results in front of the agent before it acts, so every turn starts grounded in what the user already knows and has decided. It serves the user, whose prompts arrive with their context attached, and the operator, who configures where the PKB lives and how the search authenticates.

## User stories

### US-1 Grounded prompts

As a user, I want each prompt I type searched against my PKB, so that the agent starts from my prior knowledge and decisions without my asking.

- **AC-1.1** Given a reachable, authorised PKB endpoint, when the user submits a prompt, then the agent's turn receives the matching PKB results as advisory context, marked as PKB search results.
- **AC-1.2** Given a prompt wrapped in a channel envelope (such as Telegram), when it is submitted, then the search query is the user's text inside the envelope, not the envelope.
- **AC-1.3** Given a prompt longer than 200 characters, when it is submitted, then the search query is its first 200 characters.
- **AC-1.4** Given a search whose results exceed 8,000 characters, when they are injected, then the injected text is cut to 8,000 characters and marked as truncated.
- **AC-1.5** Given a search with no matches, when the prompt is submitted, then nothing is injected.

### US-2 Peer reports stay unhydrated

As a user, I want reports from other agents left out of the search, so that a peer's claim is checked as a claim rather than dressed in PKB context.

- **AC-2.1** Given a prompt that begins with a peer-agent envelope (cross-session message, teammate message or task notification), when it is submitted, then no search runs and nothing is injected.

### US-3 Authenticated search from the environment

As an operator, I want the search to reach an access-controlled PKB endpoint using credentials I set in the environment, so that the PKB stays private and no credential ships in the plugin.

- **AC-3.1** Given `PKB_MCP_URL` and a credential in the hook's environment, when a prompt is submitted, then the search request carries that credential and the endpoint returns results.
- **AC-3.2** Given `PKB_MCP_URL` is unset, when a prompt is submitted, then no search runs and the turn proceeds.
- **AC-3.3** Given a credential set only in a client's own MCP configuration, when a prompt is submitted, then the search does not use it.

### US-4 Failures are visible and name their cause

As an operator, I want a failed search reported to the agent with the reason the endpoint gave, so that I can tell a missing credential from a dead server without re-running the hook by hand.

- **AC-4.1** Given the endpoint rejects the request for want of a valid credential (HTTP 401 or 403), when a prompt is submitted, then the turn proceeds and the injected message says the PKB endpoint refused authorisation and names the credential variables the hook reads.
- **AC-4.2** Given the endpoint is unreachable or does not answer within 5 seconds, when a prompt is submitted, then the turn proceeds and the injected message says so.
- **AC-4.3** Given any failed search, when the turn proceeds, then no other search route is tried.

## Design

**Trigger.** Hydration runs on every user prompt submission, before the agent's turn. The user prompt is the only input; peer envelopes are excluded because they carry claims awaiting verification, and grounding them would launder those claims (US-2).

**Endpoint.** The PKB is an MCP server at `PKB_MCP_URL`, reached over streamable HTTP. The hook calls its `pkb_search` tool with the query. That is the only transport: a search that fails reports its failure and stops (AC-4.3), because a quiet second route hides the fault that needs fixing.

**Credentials.** The endpoint sits behind an access-controlled gateway, so every request carries a credential. The hook reads credentials from its own process environment only (AC-3.3), from either source:

| Variable | Contents | Sent as |
| - | - | - |
| `PKB_MCP_HEADERS` | JSON object of header name to value, e.g. `{"Authorization": "Bearer <token>"}` | Each pair as an HTTP header. Malformed JSON is logged and ignored. |
| `CF_ACCESS_CLIENT_ID` + `CF_ACCESS_CLIENT_SECRET` | A Cloudflare Access service token, both halves | `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers |

The hook runs as its own process, launched by the client with the client's environment. A credential that the client itself holds for its own MCP connection (for example an OAuth token for the same gateway) is not visible to the hook; the operator supplies the hook's credential separately in the environment the client is launched from.

**Budget.** The connect-and-search is bounded at 5 seconds, because the hook runs synchronously ahead of every turn. Injected output is capped at 8,000 characters (AC-1.4).

**Output.** Results are injected as advisory context inside `<academicOps PKB search results>` tags. A failure is injected as a one-line message beginning `aops hooks: handler 'search_the_pkb' failed`, carrying the cause (US-4).
