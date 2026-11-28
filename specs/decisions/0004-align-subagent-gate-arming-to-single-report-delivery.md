---
status: "accepted"
date: 2026-11-27
decision-makers: ["user"]
---

# Align Subagent Gate Arming to Single Report Delivery

## Context and Problem Statement

Across agent harnesses, subagents report back through different combinations of message envelopes and tool results: direct synchronous tool returns (`PostToolUse` / `PostToolBatch` on `Agent` or `Task`), `SubagentHandback` delivered via `<agent-message>` with pointer stubs in `<task-notification>` and foreground dispatch responses (`handback: "send"`), named teammate `SendMessage` channels (`<teammate-message>` and `idle_notification`), and turn-start system messages on `agy`. Root coordinators receive `UserPromptSubmit` for queued messages, whereas non-root subagent coordinators on Claude Code receive only `SubagentStart`, `PreToolUse`, and `PostToolUse` / `PostToolBatch`.

Three gaps broke single-claim delivery semantics: (1) bare `SubagentHandback` pointer stubs in foreground `PostToolUse(Agent)` `content` passed `carries_report` because pointer detection only checked `<task-notification>` `<result>` tags, arming a duplicate claim on the stub and defeating foreground bridging; (2) root-destined `PostToolUse(SubagentHandback)` calls armed the root slot before `UserPromptSubmit` delivered `<agent-message>`, blocking mid-turn root actions and `Stop` on unseen reports; and (3) `teammate_spawned` aliases (`name`, `teammate_id`), pre-dispatch spawn names, resultless `idle_notification` JSON payloads, and bidirectional senderless `agent_result` pairing were incomplete. How should `hearsay_gate` arm every caller surface once per delivered report without breaking any dispatch surface?

## Considered Options

- Arm strictly on `UserPromptSubmit` envelopes and ignore `PostToolUse` / `SubagentHandback`
- Arm eagerly on every `PostToolUse` (`SubagentHandback`, `Agent`, `SendMessage`) and `UserPromptSubmit` independently
- Align gate arming to the moment and channel where each caller surface receives a report, suppress pointer/idle non-reports across all surfaces, and pair dual-channel deliveries symmetrically into one claim

## Decision Outcome

Chosen option: "Align gate arming to the moment and channel where each caller surface receives a report, suppress pointer/idle non-reports across all surfaces, and pair dual-channel deliveries symmetrically into one claim", because it guarantees one claim per report and zero unseen mid-turn blocks across every foreground, background, named/teammate, nested-coordinator, and peer-message surface.

Architectural invariants adopted:

1. **Surface-aligned handback delivery:** Child `PostToolUse(SubagentHandback)` calls resolving to a non-root subagent coordinator arm that coordinator silently immediately and bridge notices on foreground metadata-only or pointer-stubbed `PostToolUse`/`PostToolBatch(Agent)` returns (including `handbackReport` fallback when the child hook lags). Calls resolving to root or unresolved callers buffer in `parents["handbacks"]` until `UserPromptSubmit` delivers `<agent-message>` or a truly metadata-only foreground completion bridges them; pointer-stubbed foreground returns leave root buffered for `UserPromptSubmit` and reconcile stale buffer entries if the prompt won the race.
2. **Uniform non-report suppression:** Single-line `SubagentHandback` pointer stubs are ignored in `<task-notification>` `<result>`, dispatch `tool_response` payloads, and `carries_report`, while `<teammate-message>` `idle_notification` JSON without a substantive string `result` never arms the gate.
3. **Alias registration and symmetric channel pairing:** Dispatch metadata registers pre-dispatch spawn names alongside `name` and `teammate_id` (and bare `name` prefixes) onto canonical agent IDs. Active and un-superseded disarmed claims pair symmetrically between senderless foreground `agent_result` returns and named message/handback deliveries once per channel pair, superseding only when the caller resumes the child.
4. **Procedural boundary preserved:** Verdict validation and recording (`premise_check_verdict.py`) remain untouched with zero prose or Argdown syntax parsing ([ADR-0003](0003-retire-mechanical-premise-check-parser-and-adopt-administrative-law-review.md)).

### Consequences

- Good, because direct foreground returns, foreground `SubagentHandback`, background `SubagentHandback`, named teammates, intermediate coordinators, and `agy` peer messages each arm once on actual report delivery and disarm on a single verdict.
- Good, because root coordinators are never blocked mid-turn or at `Stop` by unseen queued `SubagentHandback` reports, while subagent coordinators without `UserPromptSubmit` stay gated before relaying or stopping.
- Bad, because `<session>.parents.json` retains short-lived spawn-name and buffered-handback coordination state until delivery or child resume to bridge asymmetric harness hook lifecycles.
