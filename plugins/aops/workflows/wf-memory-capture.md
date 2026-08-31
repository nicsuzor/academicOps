---
id: wf-memory-capture
title: "wf-memory-capture"
type: template
created: 2026-08-29T00:09:37.482345810+00:00
modified: 2026-08-29T00:09:37.482345810+00:00
last_modified: 2026-08-29T00:09:37.482347624+00:00
alias:
  - "wf-memory-capture-wf-memory-capture"
  - "wf-memory-capture"
permalink: wf-memory-capture
tags:
  - wf-template
---

## What this step does

Durable knowledge capture: extract and record cross-session findings, architectural decisions, operational patterns, and system insights produced during the task into the PKB or project memory. This step prevents knowledge from being trapped or lost in ephemeral session transcripts.

## Pattern

1. **Apply the durability filter**:
   - Only capture knowledge that will remain true and valuable tomorrow with this session transcript completely deleted.
   - Do NOT capture session-local ephemera, transient debugging traces, intermediate trial-and-error, or trivial command invocations.

2. **Respect the storage hierarchy**:
   - **Task/Epic state**: Task-local findings, blockers, and completion evidence belong directly on the task/epic body (`pkb__update_body` / `pkb__update_task`).
   - **Durable cross-session knowledge & architectural decisions**: PKB notes or knowledge nodes (`type: note`, `type: knowledge`, `type: memory` via `pkb__create` / `pkb__update_body` or `/remember`).
   - **Actionable follow-ups & incomplete work**: File new task nodes in the PKB (`pkb__create_task`).
   - **Issues / external bugs**: GitHub issue tracker.

3. **Integrate into existing knowledge before creating new nodes**:
   - Search first (`pkb__search` / `pkb__retrieve_memory`) to identify existing relevant documents.
   - If an existing note covers the topic, update or amend that document (`pkb__update_body` / `pkb__append`) rather than creating duplicate fragments.
   - When creating a new document, wire appropriate wikilinks (`[[document-id]]`), tags, and parent relationships.

4. **Output contract**:
   - State what durable knowledge was captured, the destination document ID(s), and the pinpoint rationale.
   - If no durable knowledge was produced (e.g., standard procedural execution with no novel findings or friction), explicitly declare zero memory capture and proceed.

## When to include

- Composed during session wrap-up / handover ([[wf-handover]], [[wf-handback]]) or triggered via `/remember` when a task yields durable architectural decisions, operational insights, or reusable discoveries.
