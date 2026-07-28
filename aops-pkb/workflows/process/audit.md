---
id: audit
kind: process
category: meta
description: Framework governance audit — structure sync, index curation, acceptance tests, persisted report
requires: [handover]
pairs-with: [monitor-prevent-bloat]
conflicts: []
version: 1.0.0
permalink: workflows-process-audit
---

# Process: Framework Audit

## When to Use

**Manual trigger** (recommended): after significant framework changes (new
skills, hooks, agents); before major releases; to re-sync docs/indices with
the filesystem. **Session-end**: optionally trigger the lighter
[[session-effectiveness]] sub-check instead — a full audit is too heavy for
routine session-end.

## Phases

1. **Structure audit** — sync filesystem to the canonical index.
2. **Index curation** — update the routing indices (this library's `INDEX.md`
   and equivalents).
3. **Documentation accuracy** — update README/flowcharts/tables to match.
4. **Acceptance tests** — run agent-driven end-to-end tests.
5. **Persist** — save the audit findings to a dated durable record.

## Constraints

**Completeness**: all phases run for a full audit. **No rationalization**:
report ALL discrepancies found — never justify skipping a file as "generated"
or "acceptable"; the user decides what's acceptable, not the auditor.
**Evidence**: every finding cites a specific file:line reference, not just a
claim.
