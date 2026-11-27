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
| 1. Capture | `/q` | one ask | Situate an ask on the graph -- placing repo-scoped tasks (strictly one per repo, consolidated across open and closed tasks, situated under governing component or initiative epics with zero leaf `serves` edges while Strategic Value Carriers wire `serves` directly to priced targets), valued at intake per [R1](graph-valuation.md#3-r1----placement-at-intake-q). |
| 2. Expand | `/decompose` | one objective (optional) | Expand an objective into an abstract graph of sub-objectives at objective altitude, decision branches, prerequisites, and alternate paths, each a node bound to no executor. Reads the record first and stops at the first unknown before implementation detail. |
| 3. Reify | `/reify` | one task about to be dispatched | Just before dispatch, the crew binds the task to its executor and composes workflows from the 3-tier library onto a single combined task body by default, written as instructions a worker can complete without further knowledge from the PKB. |
| 4. Dispatch | `/dispatch` | ready, reified tasks | Start polecat containers on queued tasks, each seeded with its task's instructions as the prompt. Writes no tasks. |

The PKB custodian (Pauli) runs Stage 1 (`/q`), optional Stage 2 (`/decompose`), and `/strategize`. Stage 3 (`/reify`) belongs to the crew, which holds the PKB and the template library. Stage 4 belongs to the dispatcher (`/dispatch`).

Execution is not a stage of the pipeline: it happens in the polecat container ([polecat-system.md](../polecat/polecat-system.md)), which has no plugins and no PKB access. The worker runs no `/pull`, `/reify`, or `/dump`, claims nothing, and writes no task status. It does the work in its one repository with incremental `git push` checkpoints and delivers pull requests; on exit the dispatch service records its final output message on the task and uploads the session log. A session with the crew installed (a crew container, Claude Code on the web, a laptop) claims and executes a task itself via `/pull`, running `/reify` in-session if needed.

The stages are operative instructions and live in `plugins/ida/skills/`. This spec does not restate them.

## Altitude: what each planning skill is about

Three planning skills sit above dispatch, told apart by the object each works on, not by how abstract its output is.

| Altitude | Skill | Object | Produces |
| - | - | - | - |
| Macro | `/strategize` | the graph as a whole | Direction: which objectives exist, how they intersect, which assumptions are load-bearing, what to do next. Thinking time; no tasks are written. Converged asks go to `/q`, adopted objectives to `/decompose`. |
| Meso | `/decompose` | one objective | Sub-objectives, forks and probes as nodes bound to no executor, expanded as far as reliable inference reaches now (optional expansion). |
| Micro | `/reify` | one task about to run | The executing task: the node bound to an executor class and a workflow composed from templates current at dispatch time on a single combined task body. |

Decomposition and reification are timed differently, for opposite reasons:

- **Decompose early (when needed).** No objective is independent; its sub-objectives are what other objectives' tasks intersect with. A task minted elsewhere (a meeting, a submission, a collaboration) can account for a decomposed part only once that part exists on the graph, so an objective is expanded as soon as it is captured, to what can reliably be inferred at that point, and stops at the first unknown.
- **Reify late, just before dispatch, on the crew's side.** A reified task fixes the executor and the workflow, and both change with circumstances. A dispatchable task that sits on the graph goes stale, so `/reify` runs at the last moment before `/dispatch`: `/q` -> `/reify` -> `/dispatch`. It cannot run later than that, because the polecat container has no plugins and no PKB access; the instructions it is dispatched with are everything the worker gets, and they are written to be completed without further knowledge from the PKB.

The boundary that separates meso from micro is executor binding: a decomposed node says what must become true and names no executor or workflow; a reified task says who runs it and how. Personal Knowledge Base queries, memory curation, and graph operations route directly to the custodian, while general web searches, filesystem lookups, and repo investigations route to internal subagents, and work that runs, measures, tests, or builds something passes through to polecats.

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
| Universal | `plugins/crew/skills/workflow-library/workflows/*.md` |
| Personal knowledge base | PKB documents carrying `type: template` and no `project` |

### Universal templates

The universal workflow library (`plugins/crew/skills/workflow-library/workflows/`) holds **28 templates**:

- `wf-code-task-base`: Foundation for code-change tasks executed via `/pull`.
- `wf-dialectical-review`: Universal default dialectical review workflow coordinating strategic coherence, compliance, and empirical verification perspectives.
- `wf-dispatch`: Direct worker dispatch workflow for headless container execution without child task creation.
- `wf-dispatch-queue`: Dispatch queue ranking ready tasks for user approval and container launch.
- `wf-doc-base`: Foundation for tasks changing instruction text or repository documentation.
- `wf-effectual-plan`: Explore strategic uncertainty, surface load-bearing assumptions, and propose bounded next steps.
- `wf-escalated-approval`: Hand a complete artifact over for an escalated explicit decision while keeping dependent work blocked.
- `wf-fact-check`: Verify factual, empirical, and citation-bearing claims against primary sources.
- `wf-finish`: Default task completion and release workflow separating work and review deliverables where required.
- `wf-interactive`: Workflow governing interactive sessions under one outer task claimed via `/q`.
- `wf-keep-analysis-data`: Persist intermediate datasets from slow or costly analyses for reuse.
- `wf-lookup`: Lightweight lookup workflow routing PKB reads, writes, curation, and graph operations to the custodian.
- `wf-pr-move-along`: Drive an open pull request through checks, proportionate review, conflict settlement, and landing.
- `wf-pr-sweep`: Sweep open pull requests across repositories in parallel, triage against merge policies, and queue next-step tasks.
- `wf-qa`: Universal empirical QA verification against live tests, probes, rendered outputs, and governing standards.
- `wf-qa-visual`: Capture and multimodally verify rendered visual outputs against criteria.
- `wf-quick-fix`: Shortened delivery route for simple, uncontroversial changes.
- `wf-rbg`: Universal compliance review against axioms, rules, authority scope, data boundaries, and enforcement hierarchy.
- `wf-reconcile`: Universal graph reconciliation and task truth-maintenance procedure.
- `wf-research`: Investigate problem spaces, prior work, and trade-offs grounded in primary evidence.
- `wf-research-and-implement`: Sequence grounded investigation, specification, independent review, and test-first implementation on one PR.
- `wf-research-output`: Sequence an academic output from direction and audience through evidence, review, and release.
- `wf-signoff`: Author a concise one-page summary digest for decision or release sign-off.
- `wf-spec`: Author a complete technical specification before implementation.
- `wf-strategic-fit`: Universal strategic-direction and PKB congruence review.
- `wf-structural-map`: Extract a four-part descriptive structural map (Aims, Methodology, Analytical theory, Contribution) of academic work.
- `wf-task-base`: Foundation for every task executed via `/pull` (schema, placement, groundwork, and boundaries).
- `wf-tdd`: Testing standards and red-green-refactor cycle for executable code changes.

**How they go together is the composing agent's judgment, not a rule here.** Which components a task needs, how they combine, and how much process the work warrants are worked out at composition time, against the task in hand.

## Authoring a component

1. **Outline, not script.** Enumerate the steps the class of work requires, each stated as an outcome the caller can recognise as met -- never the specific tool calls or prose that satisfy it this time. Several components must fit in one context window together; target ≲100 lines. Substance that outgrows that belongs in a skill the component points at -- a component orchestrates, a skill executes.
2. **Name the blanks.** Every point where a step depends on something the caller supplies -- a lens, a depth, a sibling component, an artifact shape -- is stated as a blank in that step, not silently assumed.
3. **No history or meta-commentary in the body.** A component states the current process only, per [`current-state-only`](../../.agents/rules/current-state-only.md) -- never why a step was added, what it replaced, or how the template evolved. That belongs in git.
4. **Revisable.** Components are standardised work, not law: versioned, and improved from execution feedback.

## Existence, not registration

A component exists because it carries `type: template`, not because an index lists it. Indexes help people orient; they are never the discovery mechanism, and a name absent from every index is not thereby missing.

**Enumerate by running the command, every time.** Describing what the library probably holds, from memory, is the failure this rule exists to prevent.
