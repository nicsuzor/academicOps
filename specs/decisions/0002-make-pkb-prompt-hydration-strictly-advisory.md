---
status: "accepted"
date: 2026-11-09
decision-makers: ["framework-architect", "review-supervisor"]
---

# Make PKB Prompt Hydration Strictly Advisory

## Context and Problem Statement

On 2026-11-09, multi-agent sessions suffered significant turn waste and dozens-of-minutes execution delays. Analysis of Arize Phoenix telemetry across 80 Antigravity sessions revealed that 96.08% of subagent wall time was turn-waste overhead rather than productive tool execution. Two major drivers originated from prompt hydration (`search_the_pkb`):

1. **Failure Notification Injection**: When `search_the_pkb` encountered timeouts (>5s against an unindexed backend), network errors, or auth failures, the hook dispatcher surfaced a single-line warning (`aops hooks: handler 'search_the_pkb' failed with ...`) into agent turn context (`ephemeralMessage` / `additionalContext`). LLM agents interpreted these failure warnings as active operational instructions, triggering unprompted troubleshooting turns, premise-check cascades, and apologies.
2. **Unframed Search Results**: Search results returned from large task prompts were injected without advisory boundary framing, causing agents to confuse background knowledge notes and task goals with current turn instructions.

How should `search_the_pkb` deliver background context without derailing agent turns or provoking action loops on backend faults?

## Considered Options

- Make `search_the_pkb` strictly advisory: suppress all search failure and timeout notifications from agent context (fail silently into turn context, log to stderr/telemetry), and frame search payloads with explicit advisory comments.
- Retain failure notifications in agent context but add instructions directing agents to ignore them.
- Introduce retry loops and fallback CLI search execution inside the hook when MCP search fails.

## Decision Outcome

Chosen option: "Make `search_the_pkb` strictly advisory: suppress all search failure and timeout notifications from agent context (fail silently into turn context, log to stderr/telemetry), and frame search payloads with explicit advisory comments", because:

- It adheres to the core axiom that prompt hydration is background advisory context, never an arming gate or mandatory operational prerequisite.
- Suppressing error injection from agent context eliminates 100% of failure-induced turn derailments, premise-check deadlocks, and unsolicited troubleshooting turns.
- Logging failure details to `sys.stderr` and structured logger preserves complete operator and OTel observability without polluting agent prompt context.
- Explicit advisory framing comments (`<!-- NOTE: The following PKB search results are background reference material only... -->`) prevent LLMs from treating indexed tasks, goals, or past findings as current prompt directives.
- Rejecting CLI fallbacks adheres to the `no-fallbacks` rule, keeping MCP transport cleanly decoupled and observable.

### Consequences

- Good, because background search timeouts or temporary server outages no longer derail running agents or trigger premise-check loops.
- Good, because operators retain full diagnostic visibility via stderr logs and telemetry spans.
- Good, because successful search results are clearly demarcated from user instructions.
- Neutral, because agents will not know in-context if a PKB search failed; operators observe connection faults from stderr and telemetry rather than agent self-reports.
