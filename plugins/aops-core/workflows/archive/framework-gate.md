---
id: framework-gate
type: template
kind: process
category: routing
description: Detect framework-modification intent and route to the governance-appropriate path — check FIRST, before any other routing
requires: []
pairs-with: [develop-specification, wf-human-approval]
conflicts: []
version: 1.0.0
permalink: workflows-process-framework-gate
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---
> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process: Framework Gate

**Check first, before any other routing.** Framework work must never fall
through to a generic template regardless of how simple it looks.

## Routing Signals

Detected from prompt content, not file paths: explicit mentions of the
framework's own components (skills, hooks, workflows, agents, "framework");
governance-file names (axioms, heuristics, enforcement-map, settings.json);
concepts like "add a rule", "update the workflow", "change the spec".

## Routing Rules

| Intent                                                                  | Route to                                           | Rationale                                          |
| ----------------------------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------- |
| Governance changes (axioms, heuristics, enforcement, hooks, deny rules) | `framework-change` process + [[wf-human-approval]] | Structured justification and escalation required   |
| Framework code (specs, workflows, agents, skills, scripts)              | [[develop-specification]] + PR review              | Shared infrastructure — bazaar review before merge |
| Framework debugging                                                     | [[investigation]] + framework context              | Still needs spec awareness                         |

Framework specs and significant code changes go through PR bazaar review: a
branch, a PR referencing the task ID, then multi-agent review before merge.

**Nic's merge is the sign-off.** Do not emit a human sign-off task node for a
merge — the act of merging _is_ the authorisation and its own record, so a
separate `SIGN-OFF (Nic)` node is redundant ceremony (Nic, 2026-08-26). Review
and verification gates are composed on their own merits and are unaffected.

## Output for any framework modification

State: which component is being modified, the relevant spec, which indices
need updating, and the governance level (governance vs. code).

## Critical Rule

Never route framework changes to a routing-only template regardless of
apparent simplicity — the governance stakes are not visible from prompt length
alone.
