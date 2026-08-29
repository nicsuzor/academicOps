---
id: audit
type: template
kind: process
category: meta
description: Framework governance audit — structure sync, index curation, acceptance tests, and dogfooding reflection loop
requires: [wf-handover]
pairs-with: []
conflicts: []
version: 1.1.0
permalink: workflows-process-audit
---

# Process: Framework Audit

## When to Use

**Manual trigger** (recommended): after significant framework changes (new
skills, hooks, agents); before major releases; to re-sync docs/indices with
the filesystem. A full audit is too heavy for routine session-end; for a
post-session read, invoke the `triage` skill in `retro` mode instead.

## Governance Audit Phases

1. **Structure audit** — sync filesystem to the canonical index.
2. **Index curation** — update the routing indices (this library's `INDEX.md`
   and equivalents).
3. **Documentation accuracy** — update README/flowcharts/tables to match.
4. **Acceptance tests** — run agent-driven end-to-end tests.
5. **Persist** — save the audit findings to a dated durable record.

## Dogfooding / Reflection Loop

A continuous loop for single sessions or batches:

1. **Execute** — do the work while staying aware of friction (what felt awkward,
   where clarification was needed).
2. **Observe** — log one-time friction and continue; recurring patterns (3+
   occurrences) trigger a check against existing heuristics, escalating to
   `learn` if genuinely missing.
3. **Codify** — before handover, turn observations into durable fixes: better
   workflow steps in workflow files, missing guardrails in constraint-checking,
   new heuristics via `learn`. Ask "what did I learn → what did I change?" at
   session end.

## Constraints

- **Completeness**: all phases run for a full audit.
- **No rationalization**: report ALL discrepancies found — never justify skipping
  a file as "generated" or "acceptable"; the user decides what's acceptable,
  not the auditor.
- **Evidence**: every finding cites a specific file:line reference, not just a
  claim.
