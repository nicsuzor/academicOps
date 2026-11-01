---
title: Workflow -- the four-stage pipeline
type: spec
category: workflow
status: ready
tags: [spec, workflow, composition, pipeline]
---

# Workflow

Work moves through four stages. Each runs, then stops; no stage fires the next.

| Stage | Skill | Object | What it does |
| - | - | - | - |
| 1. Capture | `/q` | one ask | Situate an ask on the graph -- under the right parent, wired to what it serves, valued at intake per [R1](graph-valuation.md#3-r1----placement-at-intake-q). |
| 2. Expand | `/decompose` | one objective | Expand the objective into an abstract graph of sub-objectives at objective altitude, decision branches, prerequisites, and alternate paths, each a node bound to no executor. Reads the record first and stops at the first unknown before implementation detail. |
| 3. Reify | `/reify` | one node, next to run | Bind the node to its executor and the workflow templates current now: assemble the workflow and write the dispatchable task to the graph. |
| 4. Dispatch | `/dispatch` | ready tasks | Start polecat workers on queued, ready tasks. Writes no tasks. |

The PKB custodian (Pauli) runs stages 1-3 and `/strategize`; an agent that receives one of these asks hands it to them. Stage 4 belongs to the dispatcher.

The stages are operative instructions and live in `plugins/ida/skills/`. This spec does not restate them.

## Altitude: what each planning skill is about

Three planning skills sit above dispatch, told apart by the object each works on, not by how abstract its output is.

| Altitude | Skill | Object | Produces |
| - | - | - | - |
| Macro | `/strategize` | the graph as a whole | Direction: which objectives exist, how they intersect, which assumptions are load-bearing, what to do next. Thinking time; no tasks are written. Converged asks go to `/q`, adopted objectives to `/decompose`. |
| Meso | `/decompose` | one objective | Sub-objectives, forks and probes as nodes bound to no executor, expanded as far as reliable inference reaches now. |
| Micro | `/reify` | one node | The dispatchable task: the node bound to an executor class and a workflow composed from the templates current at that moment. |

The three are timed differently, for opposite reasons:

- **Decompose early.** No objective is independent; its sub-objectives are what other objectives' tasks intersect with. A task minted elsewhere (a meeting, a submission, a collaboration) can account for a decomposed part only once that part exists on the graph, so an objective is expanded as soon as it is captured, to what can reliably be inferred at that point, and stops at the first unknown.
- **Reify late.** A reified task fixes the executor and the workflow, and both change with circumstances. A dispatchable task that sits on the graph goes stale, so a node is reified when it is next to run and not before; a node blocked on something outside the graph's control stays unreified until that clears.

The boundary that separates meso from micro is executor binding: a decomposed node says what must become true and names no executor or workflow; a reified task says who runs it and how. Lookups and questions pass through neither: the session that receives them answers them.

## Workflow components

A workflow component is a short outline of the steps a class of work requires -- not a script. It names what must happen and in what order, and leaves a **blank** at every point where the executing agent supplies something the component cannot fix in advance: which lens reviews it, how deep verification runs, who else gets pulled in, what the artifact itself looks like. A component that fills in every blank stops composing -- it becomes the one process it happens to describe.

Two things keep a component composable:

- **Steps are outcomes, not instructions.** State what must be true when a step completes ("criteria are locked before evidence is gathered"), not the keystrokes that get there. An abstract step accepts whatever the caller's context supplies to satisfy it; a prescriptive one only accepts its own.
- **Blanks are named, not hidden.** Where a step depends on something outside the component's own authority -- a review lens, a depth setting, a companion component -- the step says so, so the composing agent knows exactly what to bring.

Carries `type: template`. An agent reads a component and composes it in context, by comprehension -- never parsed, never solved.

Components come from three sources:

| Source | Where |
| - | - |
| Project | PKB documents carrying `type: template` and the task's `project`, id `<project>-<slug>` |
| Universal | `plugins/ida/skills/workflow-library/workflows/*.md` |
| Personal knowledge base | PKB documents carrying `type: template` and no `project` |

### Universal templates

Universal baseline templates in `plugins/ida/skills/workflow-library/workflows/` include:

- `wf-code-task-base`: Foundation for standard code-change tasks (test-first build, PR, independent review).
- `wf-finish`: Universal fallback finish policy (PR into base development branch, QA review).
- `wf-quick-fix`: Shortened route for simple, uncontroversial project changes (repository-allowed shortened PR or merge route, review exemption when unit and destination tests pass).
- `wf-reconcile`: Universal graph reconciliation and task truth-maintenance procedure.
- `wf-tdd`: Test-driven development red-green-refactor cycle.

**How they go together is the composing agent's judgment, not a rule here.** Which components a task needs, how they combine, and how much process the work warrants are worked out at composition time, against the task in hand.

## Authoring a component

1. **Outline, not script.** Enumerate the steps the class of work requires, each stated as an outcome the caller can recognise as met -- never the specific tool calls or prose that satisfy it this time. Several components must fit in one context window together; target ≲100 lines. Substance that outgrows that belongs in a skill the component points at -- a component orchestrates, a skill executes.
2. **Name the blanks.** Every point where a step depends on something the caller supplies -- a lens, a depth, a sibling component, an artifact shape -- is stated as a blank in that step, not silently assumed.
3. **No history or meta-commentary in the body.** A component states the current process only, per [`synthesize-not-accrete`](../../lib/axioms/synthesize-not-accrete.md) -- never why a step was added, what it replaced, or how the template evolved. That belongs in git.
4. **Revisable.** Components are standardised work, not law: versioned, and improved from execution feedback.

## Existence, not registration

A component exists because it carries `type: template`, not because an index lists it. Indexes help people orient; they are never the discovery mechanism, and a name absent from every index is not thereby missing.

**Enumerate by running the command, every time.** Describing what the library probably holds, from memory, is the failure this rule exists to prevent.
