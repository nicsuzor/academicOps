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

A workflow component is a short outline of the steps a class of work requires — not a script. It names what must happen and in what order, and leaves a **blank** at every point where the executing agent supplies something the component cannot fix in advance: which lens reviews it, how deep verification runs, who else gets pulled in, what the artifact itself looks like. A component that fills in every blank stops composing — it becomes the one process it happens to describe.

Two things keep a component composable:

- **Steps are outcomes, not instructions.** State what must be true when a step completes ("criteria are locked before evidence is gathered"), not the keystrokes that get there. An abstract step accepts whatever the caller's context supplies to satisfy it; a prescriptive one only accepts its own.
- **Blanks are named, not hidden.** Where a step depends on something outside the component's own authority — a review lens, a depth setting, a companion component — the step says so, so the composing agent knows exactly what to bring.

Carries `type: template`. An agent reads a component and composes it in context, by comprehension — never parsed, never solved.

Components come from three sources:

| Source                  | Where                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| Project-local           | `$CWD/.agents/templates/*.md` — an absent directory is empty, not an error                 |
| Plugin                  | `plugins/aops/workflows/*.md`, with the routing index at `plugins/aops/workflows/INDEX.md` |
| Personal knowledge base | documents carrying `type: template`                                                        |

**How they go together is the composing agent's judgment, not a rule here.** Which components a task needs, how they combine, and how much process the work warrants are worked out at composition time, against the task in hand.

## Authoring a component

1. **Frontmatter schema.** Every component declares its identity, category (`process`, `gate`, or `fragment`), indexable description (routing trigger and exclusions), and tags:
   ```yaml
   ---
   title: <human name>
   type: template
   category: process | gate | fragment
   description: <what it does; when to select, and when not to>
   tags: [...]
   ---
   ```
2. **Outline, not script.** Enumerate the steps the class of work requires, each stated as an outcome the caller can recognise as met — never the specific tool calls or prose that satisfy it this time. Several components must fit in one context window together; target ≲100 lines. Substance that outgrows that belongs in a skill the component points at — a component orchestrates, a skill executes.
3. **Name the blanks.** Every point where a step depends on something the caller supplies — a lens, a depth, a sibling component, an artifact shape — is stated as a blank in that step (`<blank>`), not silently assumed.
4. **No history or meta-commentary in the body.** A component states the current process only, per [`synthesize-not-accrete`](../../lib/axioms/synthesize-not-accrete.md) — never why a step was added, what it replaced, or how the template evolved. That belongs in git.
5. **Revisable.** Components are standardised work, not law: versioned, and improved from execution feedback.

## Existence, not registration

A component exists because it carries `type: template`, not because an index lists it. Indexes help people orient; they are never the discovery mechanism, and a name absent from every index is not thereby missing.

**Enumerate by running the command, every time.** Describing what the library probably holds, from memory, is the failure this rule exists to prevent.
