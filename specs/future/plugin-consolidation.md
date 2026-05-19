---
id: future-02af69a8
title: Plugin Skill Consolidation Tasks
status: inbox
created: 2026-04-10
context: "PR #499 audit identified overlap and redundancy across aops-core skills"
---

# Plugin Skill Consolidation

Queue these as PKB tasks when MCP is available.

## Merges

### Merge burst-supervisor → swarm-supervisor

- Absorb behavioral improvements from burst-supervisor into swarm-supervisor:
  - Parallel dispatch using `run_in_background: true`
  - Polecat fail-fast guard (HALT-if-polecat-missing)
  - Gemini worker commit verification block
  - "Reuse existing worker task" instruction
  - P#30 "Own every problem" axiom section
- Then delete burst-supervisor skill

### Merge decision-apply + process-bundle

- Both do the same thing: process annotated decisions → update tasks/draft emails
- Only difference: source document (daily note vs. briefing bundle)
- Merge into single skill with routing by source doc type

### Consolidate recap into daily

- `recap` and `daily` both read session summary JSONs and build narrative
- `daily` already has "Session Flow" section with identical filtering rules
- Make recap's multi-day range a mode of daily (e.g., `/daily recap 7d`)
- Delete standalone recap skill

## Deletions

### Delete eval

- Stub that says "merged into /qa" — no unique content

### Delete hypervisor

- Its own SKILL.md says "use swarm-supervisor instead"
- Preserve atomic locking patterns as a reference section in swarm-supervisor if not already there

### Delete reflect

- Thin wrapper that just invokes `/daily`
- No standalone value

### Delete assess-hydrator

- No longer needed per user decision

## Fixes

### Fix session-insights PKB sync

- Currently syncs to PKB directly, bypassing `/remember`'s search-first guard
- Should route through `/remember` to avoid duplicate entries

## Notes

- `garden` maintenance functions overlap with `/sleep` Phase 4 (staleness sweep via `triage_tasks.py`) — consider whether garden should be absorbed into sleep or remain standalone
- `extract` → `remember` pipeline boundary is fuzzy for unstructured input — clarify routing rules
