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
| 3. Reify | `/reify` | one task about to be dispatched | Just before dispatch, the PKB custodian (`pauli`) binds the task to its executor and composes workflows from the 3-tier library onto a single combined task body by default, written as instructions a worker can complete without further knowledge from the PKB. |
| 4. Dispatch | `/dispatch` | ready, reified tasks | Start polecat containers on queued tasks, each seeded with the full task as the prompt. Writes no tasks and sweeps for no completions. |

The PKB custodian (Pauli) runs Stage 1 (`/q`), optional Stage 2 (`/decompose`), and `/strategize`. On a dispatching surface Pauli also runs Stage 3 (`/reify`), before the sub-coordinator hands the task to the dispatcher. Stage 4 belongs to the dispatcher (`/dispatch`).

Execution is not a stage of the pipeline: it happens in the polecat container ([polecat-system.md](../polecat/polecat-system.md)), which has no plugins and no PKB access. The worker runs no `/pull`, `/reify`, or `/dump`, claims nothing, and writes no task status. It does the work in its one repository with incremental `git push` checkpoints and delivers pull requests; as the container is reaped, the polecat service writes the completed task to the PKB and uploads the session log. A session with the crew installed (a crew container, Claude Code on the web, a laptop) claims and executes a task itself via `/pull`, running `/reify` in-session if needed.

The stages are operative instructions and live in `plugins/crew/skills/` and `plugins/sara/skills/`. This spec does not restate them.

## Altitude: what each planning skill is about

Three planning skills sit above dispatch, told apart by the object each works on, not by how abstract its output is.

| Altitude | Skill | Object | Produces |
| - | - | - | - |
| Macro | `/strategize` | the graph as a whole | Direction: which objectives exist, how they intersect, which assumptions are load-bearing, what to do next. Thinking time; no tasks are written. Converged asks go to `/q`, adopted objectives to `/decompose`. |
| Meso | `/decompose` | one objective | Sub-objectives, forks and probes as nodes bound to no executor, expanded as far as reliable inference reaches now (optional expansion). |
| Micro | `/reify` | one task about to run | The executing task: the node bound to an executor class and a workflow composed from templates current at dispatch time on a single combined task body. |

Decomposition and reification are timed differently, for opposite reasons:

- **Decompose early (when needed).** No objective is independent; its sub-objectives are what other objectives' tasks intersect with. A task minted elsewhere (a meeting, a submission, a collaboration) can account for a decomposed part only once that part exists on the graph, so an objective is expanded as soon as it is captured, to what can reliably be inferred at that point, and stops at the first unknown.
- **Reify late, just before dispatch, by the custodian.** A reified task fixes the executor and the workflow, and both change with circumstances. A dispatchable task that sits on the graph goes stale, so `/reify` runs at the last moment before `/dispatch`: `/q` -> `/reify` -> `/dispatch`. It cannot run later than that, because the polecat container has no plugins and no PKB access; the task it is dispatched with is everything the worker gets, and its instructions are written to be completed without further knowledge from the PKB.

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

The universal workflow library (`plugins/crew/skills/workflow-library/workflows/`) holds **25 templates**, grouped by the label that opens each description (who runs it). Work templates carry no review stage: handed-back work is reviewed separately, by the `Review:` templates.

**Worker**

- `wf-code-task-base`: Change files in one repository -- code, docs, instructions or config -- run the checks the repository already has, and commit to the working branch.
- `wf-escalated-approval`: Stop at a real approval boundary -- external audience, a merge no ruling covers, unbounded cost, an outside party's approval, or a hold the user reserved -- leaving the finished artifact on the record.
- `wf-finish`: How a task ends -- output where the task says, acceptance ticked with evidence, one release status.
- `wf-keep-analysis-data`: Persist intermediate datasets from slow, costly, or hard-to-reproduce analyses so follow-up queries and revised assumptions reuse saved data without re-collection.
- `wf-research`: Find something out -- answer a question about a system, field or option set from primary evidence, with a recommendation where one is asked for.
- `wf-spec`: Write a technical specification for a non-trivial feature or change -- problem, users, scope, design, interfaces and acceptance.
- `wf-structural-map`: Extract a four-part descriptive structural map (Aims, Methodology, Analytical theory, Contribution) of academic work without evaluation or rewriting.
- `wf-task-base`: The base every task carries -- goal, acceptance, where the output goes, and the report. Use alone for any task no narrower base fits.
- `wf-tdd`: Red-green test cycle for a code change, only in repositories that already keep a test suite.

**Review**

- `wf-dialectical-review`: The default review of handed-back work -- a coordinator sizes the review to the stakes, sends only the lenses the work needs, and reconciles their verdicts into PASS, REVISE or FAIL.
- `wf-empirical-review`: Measure how agents, workflows, checks or tools perform, from the trace store of real sessions only -- never synthetic, constructed or simulated runs, or earlier reports' figures.
- `wf-fact-check`: Check the factual, empirical and citation claims in a draft against their sources. Skip for pure judgement or style.
- `wf-qa-visual`: How to capture and judge rendered visual output inside a quality review.
- `wf-qa`: Quality lens -- check the real artifact, as its audience meets it, against its requirements and purpose, returning PASS, REVISE or FAIL.
- `wf-rbg`: Rule-compliance lens -- judge an artifact, change or decision against the axioms, user and project rules, scope of authority and data boundaries, returning PASS, REVISE or FAIL.
- `wf-strategic-fit`: Strategic-fit lens -- is the work solving the right problem, as simply as it could, consistently with existing work and decisions, returning PASS, REVISE or FAIL.

**Planning**

- `wf-effectual-plan`: Explore strategic uncertainty, surface load-bearing assumptions, and propose bounded high-information next steps without executing them.
- `wf-research-output`: The stages of an academic output (paper, report, essay, talk, dataset) from question to finished draft. Used to decompose an initiative, not as one worker task.

**Crew**

- `wf-dispatch-queue`: The custodian ranks ready tasks, the front agent puts them to the user with a recommendation each, and the dispatcher starts workers on the ones approved.
- `wf-dispatch`: Hand a reified task to the dispatcher to run in a worker container, with no child tasks and no claim or release ceremony.
- `wf-interactive`: How an interactive session is run -- one outer task, delegation to internal delegates, checked seams, and one handover.
- `wf-lookup`: PKB reads and writes, memory curation, graph operations and overlap checks -- straight to the custodian, with no task and no ceremony.
- `wf-pr-move-along`: Take one open pull request to merged, or to a clearly recorded reason it cannot merge yet, under the repository's merge rules.
- `wf-pr-sweep`: Triage every open pull request in one or more repositories, queue the next step for each, and report a disposition for all of them.
- `wf-reconcile`: Bring the task graph back in line with reality -- advance open asks, sync PRs and releases, clear agent work out of review, settle failed tasks, reset stale claims, and surface prepared user decisions to the daily note.

**How they go together is the composing agent's judgment, not a rule here.** Which components a task needs, how they combine, and how much process the work warrants are worked out at composition time, against the task in hand.

## Authoring a component

1. **Outline, not script.** Enumerate the steps the class of work requires, each stated as an outcome the caller can recognise as met -- never the specific tool calls or prose that satisfy it this time. Several components must fit in one context window together; target ≲100 lines. Substance that outgrows that belongs in a skill the component points at -- a component orchestrates, a skill executes.
2. **Name the blanks.** Every point where a step depends on something the caller supplies -- a lens, a depth, a sibling component, an artifact shape -- is stated as a blank in that step, not silently assumed.
3. **No history or meta-commentary in the body.** A component states the current process only, per [`current-state-only`](../../.agents/rules/current-state-only.md) -- never why a step was added, what it replaced, or how the template evolved. That belongs in git.
4. **Revisable.** Components are standardised work, not law: versioned, and improved from execution feedback.

## Existence, not registration

A component exists because it carries `type: template`, not because an index lists it. Indexes help people orient; they are never the discovery mechanism, and a name absent from every index is not thereby missing.

**Enumerate by running the command, every time.** Describing what the library probably holds, from memory, is the failure this rule exists to prevent.
