---
id: workflows-workflow
title: Workflow — the three-stage pipeline
type: spec
category: workflow
status: ready
tags: [spec, workflow, composition, pipeline]
---

# Workflow

Work moves through three stages. Each runs, then stops; no stage fires the next.

| Stage      | Skill        | What it does                                                                                                                                              |
| ---------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Capture | `/q`         | Situate an ask on the graph — under the right parent, wired to what it serves, valued at intake.                                                          |
| 2. Expand  | `/decompose` | Expand the objective into an abstract graph of sub-objectives, decision branches, prerequisites, and alternate paths. Stops before implementation detail. |
| 3. Reify   | `/brief`     | Work out the process, cut into dispatchable units, and write the brief and acceptance criteria.                                                           |

The stages are operative instructions and live in `plugins/aops/skills/`. This spec does not restate them.

## Workflow components

A workflow component is a short markdown file, or knowledge-base document, carrying `type: template`. An agent reads it and composes it in context, by comprehension — never parsed, never solved.

Components come from three sources:

| Source                  | Where                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| Project-local           | `$CWD/.agents/templates/*.md` — an absent directory is empty, not an error                 |
| Plugin                  | `plugins/aops/workflows/*.md`, with the routing index at `plugins/aops/workflows/INDEX.md` |
| Personal knowledge base | documents carrying `type: template`                                                        |

**How they go together is the composing agent's judgment, not a rule here.** Which components a task needs, how they combine, and how much process the work warrants are worked out at composition time, against the task in hand.

## Authoring a component

1. **Short and composable.** Several must fit in one context window together; target ≲100 lines. Substance that outgrows that belongs in a skill the component points at — a component orchestrates, a skill executes.
2. **Intent and acceptance criteria, not micro-scripting.**
3. **Revisable.** Components are standardised work, not law: versioned, and improved from execution feedback.

## Existence, not registration

A component exists because it carries `type: template`, not because an index lists it. Indexes help people orient; they are never the discovery mechanism, and a name absent from every index is not thereby missing.

**Enumerate by running the command, every time.** Describing what the library probably holds, from memory, is the failure this rule exists to prevent.
