---
name: skills
title: aops-extras Skills Index
type: index
category: tools
description: Index of the workflow-system pipeline skills, evaluation skills, and the workflow template library
permalink: aops-extras-skills
tags: [tools, routing, skills, index, extras, workflow-system, pipeline]
---

# aops-extras Skills Index

Home of the **workflow-system pipeline** — the successor to enforcement-heavy process. The framework
stops policing _how_ agents work; instead it articulates what is wanted (pipeline skills) and evaluates
what comes back (evaluation skills). Design specs: `~/brain/specs/drafts/workflow-system/`
([[00-pipeline]], [[10-workflow-library]], [[20-skill-requirements]], [[two-layer-decomposition]]).

## Pipeline skills (a task moves through these five stages)

| Skill       | Stage       | What it does                                                                       | Personality                   |
| ----------- | ----------- | ---------------------------------------------------------------------------------- | ----------------------------- |
| `hydrate`   | 2 Hydrate   | Put any ask/task in full current context — the trust precondition (context bundle) | agnostic                      |
| `situate`   | 3 Situate   | Turn a hydrated ask into ONE valued, graph-placed task; mark `needs_decomposition` | pauli                         |
| `decompose` | 4 Decompose | When a task comes due: unexploded subtask DAG + composed process/gate regime       | pauli                         |
| `brief`     | 5 Brief     | At dispatch: expand the due subtask into a seven-element delegation brief          | agnostic (briefer ≠ executor) |

Stage 1 (Intake) is the inbound ask; Execute/Evaluate are the tail. `hydrate`→`situate` may run in one
conversational turn; `decompose` and `brief` run just-in-time when work comes due (rolling-wave).

## Evaluation skills (the EVALUATE stage — judge returned work against the brief)

| Skill              | Role                                                                                                           |
| ------------------ | -------------------------------------------------------------------------------------------------------------- |
| `verify`           | Assume-broken runtime QA (marsha) — quality + claim-reliability lenses; thin emitted evidence is itself a FAIL |
| `strategic-review` | Axiom/premise/strategy review (rbg + pauli + james) — compliance lens; critique addressed to the brief         |

## Graph maintenance

| Skill               | What it does                                                                          | Personality |
| ------------------- | ------------------------------------------------------------------------------------- | ----------- |
| `graph-maintenance` | Wire `contributes_to` edges + keep the task graph structurally sound (garden/densify) | pauli       |

## Workflow template library

`workflows/` is the shared substrate the pipeline composes from — read and composed **in-context, by
comprehension**, never parsed. Single index: [`workflows/INDEX.md`](workflows/INDEX.md).

- `workflows/gates/` — reusable QA/vetting/approval obligations with declared stakes + door-type
  (verification, qa, outbound-review, handover, constraint-check, human-approval). Door-type policy
  selects _which gates get composed in_.
- `workflows/process/` — how a class of work proceeds (feature-dev, peer-review, email-triage,
  investigation, …) plus composable fragments (task-tracking, tdd, batch, burst, memory-capture).

## Supersession

These skills replace the former `planner` and `hydrator` skills (previously in `aops-pkb/skills/`):
capture/plan → `situate`; decompose → `decompose`; wire/garden/maintain → `graph-maintenance`;
hydrator + its embedded workflow library → `hydrate` + the peer `workflows/` library. The old skills
were deleted (git preserves history); "Trust the Worker" authoring doctrine relocated to
[`skills/brief/references/authoring-discipline.md`](skills/brief/references/authoring-discipline.md).
