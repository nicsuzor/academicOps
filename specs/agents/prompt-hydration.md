---
title: Prompt Hydration
status: ready
---

# Prompt Hydration

Prompt hydration searches the PKB on top-level `ida` turns with each real user prompt from an interactive console or incoming channel message (`<channel ...>`) and puts the results in front of the agent before it acts, so every user turn starts grounded in what the user already knows and has decided. Non-`ida` agents, unnamed sessions, subagents, automated wakeups, peer reports, subagent handbacks, and task notifications do not trigger hydration. It serves the user, whose prompts arrive with their context attached, and the operator, who configures where the PKB lives and how the search authenticates.

## User stories

### US-1 Grounded user prompts and incoming channel messages for top-level Ida

As a user, I want each prompt I type at an interactive console or send over a channel to a top-level `ida` agent searched against my PKB, so that `ida` starts from prior knowledge and decisions without my asking, while subagents, other agents, automated wakeups, and agent-to-agent messages stay unhydrated.

- **AC-1.1** Given a reachable, authorised PKB endpoint and a top-level `ida` agent session (`agent_type` resolving to `ida` with no subagent `agent_id` or subagent conversation ancestry), when a real user prompt or incoming `<channel ...>` message is submitted, then the agent's turn receives the matching PKB results as advisory context, marked as PKB search results.
- **AC-1.2** Given a prompt wrapped in a `<channel ...>` envelope (such as Telegram or Discord), when it is submitted and its unwrapped body is not a peer, agent, task, command, or reminder wrapper, then the search query is the text inside the `<channel>` envelope, not the envelope.
- **AC-1.3** Given a prompt longer than 8 KB (8,192 characters), when it is submitted, then the search query is capped at 8 KB (8,192 characters); prompts up to 8 KB are sent whole without 200-character truncation.
- **AC-1.4** Given a search whose results exceed 8,000 characters, when they are injected, then the injected text is cut to 8,000 characters and marked as truncated.
- **AC-1.5** Given a search with no matches or empty content, when the prompt is submitted, then nothing is injected.
- **AC-1.6** Given a top-level `ida` `agy` invocation (`invocationNum` 0), whose hook payload carries no prompt, when the turn starts from a `USER_INPUT` step (not a `SYSTEM_MESSAGE` wake), then the search query is the text inside `<USER_REQUEST>` of the transcript's latest `USER_INPUT` step (stripping any leading `<CONTEXT_SUMMARY>` when `<USER_REQUEST>` tags are absent).
- **AC-1.7** Given an agy turn, when a later model invocation in the same turn starts (`invocationNum` above 0), then no search runs.
- **AC-1.8** Given a slash command prompt other than `/pull` or `/ida:pull` with an argument (`/cmd <arg>`), when it is submitted, then the search query is the `<arg>` text whole up to 8 KB.
- **AC-1.9** Given a PKB search request over MCP, when the call is made, then `arguments` carries `detail: "snippet"`, `limit: 5`, and `_session` containing `session_id`, `prompt_id`, `agent_id`, `caller: "hook"`, and `surface`, with `prompt_id` matching the turn hook span.
- **AC-1.10** Given a non-`ida` agent, an unnamed session, a subagent (`agent_id` set or subagent conversation ancestry), an `agy` `SYSTEM_MESSAGE` turn, an automated wakeup (`author` in `loop_wakeup`, `schedule_wakeup`, `poll_event`), a non-`<channel>` `author: "system"` prompt, or a peer/agent/task/command/reminder wrapper (such as `<cross-session-message>`, `<teammate-message>`, `<task-notification>`, `<subagent-handback>`, `<agent-message>`, `<handback>`, `<local-command-*>`, `<command-message>`, `<system-reminder>`, `<subagent_reminder>`, `<scheduled-*>`, or `Another Claude session sent a message:`, even when nested inside `<channel>`), when it arrives, then no PKB search runs and nothing is injected.

### US-2 Argument-less slash commands and `/pull` make no search calls

As a user, I want argument-less slash commands and `/pull` invocations to make no PKB search calls, so that routine session lifecycle actions and commands do not trigger unnecessary network traffic.

- **AC-2.1** Given an argument-less slash command (`/cmd`), or `/pull` / `/ida:pull` (bare or with arguments), when it is submitted, then no search runs and nothing is injected.

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

**Trigger.** Hydration fires synchronously before the agent's turn on `UserPromptSubmit` (`PreInvocation` on `agy`) when all of the following hold (see `AC-1.1`–`AC-1.10`, `AC-2.1`):

- **Session eligibility**: Top-level `ida` sessions only (`agent_type` resolved from client payload aliases, Linux `agy` `--agent` CLI ancestry, or `CLAUDE_AGENT_NAME`/`AGY_AGENT_NAME`/`AOPS_AGENT_NAME`), with empty `agent_id` and no subagent conversation ancestry.
- **Eligible inputs**: Real user prompts from an interactive console, a single `<channel>` envelope (unwrapped), or `/cmd <arg>` (searching `<arg>` whole up to 8 KB); on `agy`, strictly `USER_INPUT` turns at `invocationNum == 0` (extracting `<USER_REQUEST>` or stripping leading `<CONTEXT_SUMMARY>`).
- **Exclusions**: Non-`ida` agents, unnamed sessions, subagents, `agy` `SYSTEM_MESSAGE` or continuation turns (`invocationNum > 0`), automated wakeups, non-`<channel>` system turns, peer/agent/task/command/reminder wrappers (outer or nested), bare `/cmd`, and `/pull` / `/ida:pull` make zero PKB calls.

**Endpoint.** The PKB is an MCP server at `PKB_MCP_URL`, reached via a single streamable-HTTP POST to PKB_MCP_URL. The hook calls its search tool (prefixed by `PKB_MCP_TOOL_PREFIX`, default `pkb_search`) with the query, requesting concise snippets (`detail: "snippet"`) and top 5 results (`limit: 5`) to preserve prompt token budget while providing title, score, priors, ID, tags, and body excerpt for relevant entries. If the endpoint requires an MCP session, the hook falls back to `initialize` once and caches the session ID for 24 hours in the tracer state dir. Requests carry `x-session-id`, `traceparent` from the active turn, a non-urllib `User-Agent`, and any resolved credential headers (unauthenticated when unset so the cloud proxy injects them). Tool call arguments carry the query, `detail: "snippet"`, `limit: 5`, and a reserved `_session` attribution object (`session_id`, `prompt_id`, `agent_id`, `caller: "hook"`, `surface`), with `prompt_id` matching the turn hook span (AC-1.9). That is the only transport: a search that fails reports its failure and stops (AC-4.3), because a quiet second route hides the fault that needs fixing.

**Credentials.** The endpoint sits behind an access-controlled gateway, so every request carries a credential. The hook reads credentials from its own process environment only (AC-3.3). The hook and runtime expect a single canonical set of Cloudflare Access service-token variable names; launching applications substitute the appropriate keys for different surfaces and use cases:

| Variable | Contents | Sent as |
| - | - | - |
| `DISPATCHER_MCP_TOKEN_ID` + `DISPATCHER_MCP_TOKEN_SECRET` | Canonical Cloudflare Access service token pair. The hook itself and everything running in the framework expects only this set of names. Launching applications substitute the appropriate key values (such as worker-scoped credentials without polecat dispatch access for isolated worker containers). | `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers |

The hook runs as its own process, launched by the client with the client's environment. A credential that the client itself holds for its own MCP connection (for example an OAuth token for the same gateway) is not visible to the hook; the operator or launching application supplies the hook's credential in the environment the client is launched from.

**Budget.** The connect-and-search is bounded at 5 seconds, because the hook runs synchronously ahead of every turn. Search queries are capped at 8 KB (8,192 characters). Injected output is capped at 8,000 characters (AC-1.4).

**Output.** Results are injected as advisory context inside `<academicOps PKB search results>` tags. When the server returns no matches or empty content, nothing is injected (AC-1.5). A failure is injected as a single-line message beginning `aops hooks: handler 'search_the_pkb' failed with`, carrying the cause (US-4).
