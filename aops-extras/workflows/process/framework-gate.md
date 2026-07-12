---
id: framework-gate
kind: process
category: routing
description: Detect framework-modification intent and route to the governance-appropriate path — check FIRST, before any other routing
requires: []
pairs-with: [develop-specification, human-approval]
conflicts: []
version: 1.0.0
permalink: workflows-process-framework-gate
---

# Process: Framework Gate

**Check first, before any other routing.** Framework work must never fall
through to a generic template regardless of how simple it looks.

## Routing Signals

Detected from prompt content, not file paths: explicit mentions of the
framework's own components (skills, hooks, workflows, agents, "framework");
governance-file names (axioms, heuristics, enforcement-map, settings.json);
concepts like "add a rule", "update the workflow", "change the spec".

## Routing Rules

| Intent                                                                  | Route to                                        | Rationale                                          |
| ----------------------------------------------------------------------- | ----------------------------------------------- | -------------------------------------------------- |
| Governance changes (axioms, heuristics, enforcement, hooks, deny rules) | `framework-change` process + [[human-approval]] | Structured justification and escalation required   |
| Framework code (specs, workflows, agents, skills, scripts)              | [[develop-specification]] + PR review           | Shared infrastructure — bazaar review before merge |
| Framework debugging                                                     | [[investigation]] + framework context           | Still needs spec awareness                         |

Framework specs and significant code changes go through PR bazaar review: a
branch, a PR referencing the task ID, then multi-agent + human review before
merge.

## Output for any framework modification

State: which component is being modified, the relevant spec, which indices
need updating, and the governance level (governance vs. code).

## Critical Rule

Never route framework changes to a routing-only template regardless of
apparent simplicity — the governance stakes are not visible from prompt length
alone.
