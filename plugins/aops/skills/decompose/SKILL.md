---
name: decompose
type: command
description: Stage 2 Expansion — expand one situated objective into an abstract graph of sub-objectives, decision branches, implied prerequisites, and alternate paths. Stops before implementation detail.
allowed-tools: [Skill, AskUserQuestion, Read, Grep, Glob, Bash, mcp__services__pkb__get_task, mcp__services__pkb__create_task, mcp__services__pkb__update_task, mcp__services__pkb__update_body, mcp__services__pkb__search, mcp__services__pkb__task_search, mcp__services__pkb__batch_reparent]
---

# /decompose — Expand an objective into an abstract graph

Take one situated objective and expand it into the smaller, simpler components it implies: an indeterminate, abstract graph of sub-objectives, decision branches, implied prerequisites, and potential alternate paths.

Abstract means it says what, never how. If you are writing how a component gets done, you have run past the end of this stage.

## Workflow

1. **Read before you expand.**
   Front-load reconnaissance: a parallel read-only fan-out across the codebase, the graph, history, and runtime environments, before decomposing anything. Verify world-claims — paths, schemas, deployed states, negative capability claims — concurrently and **against reality, not another node**. A decomposition built on a dead premise expands the error instead of the objective. Where a load-bearing premise is dead, record what is no longer true and stop: there is nothing to expand.

2. **Start from the means.**
   What actually exists — what is built, what is known, who is available, which constraints are real. The work is what those afford, not what the goal demands.

3. **Expand to the limit of reliable inference, and no further.**
   - Model components only as far as you can draw a reliable inference.
   - Where you are reasonably confident about the alternatives that will eventually be available, **fork the graph at that point** and outline each option as its own node.
   - Keep going while you are reasonably confident and adding value.
   - **Stop before you hit implementation details.**
   - Depth tracks rigor, not just uncertainty: a component whose correctness needs checking splits into its decision and its validation as separate nodes, even where both are certain enough to decide now.

4. **Sort the assumptions, route the unknowns.**
   Sort every assumption into tested versus hoped. For each unknown:
   - **DECIDE** — a clear best option exists: make the call and record it in one bullet. If you can decide yourself, do not block; do not manufacture a roadblock where minimal effort settles the question.
   - **DEFER** — the missing input is runtime data: say what is missing, and **mint the probe** — the cheapest piece of work that yields the deciding information (`classification: spike`). Wire the blocked node `depends_on` the probe. A probe usually belongs elsewhere on the graph, not as a sibling or parent of what it blocks.
   - **SURFACE** — a genuine trade-off, a wide blast radius, or the user's own intent: represent the competing alternatives as **mutually exclusive option nodes** on the graph. Choosing an option branch completes/adopts it and cancels the competing option, unblocking downstream dependencies. **Never create a standalone "decision" task.**

   Every load-bearing assumption carries a confidence level and a contingency — what the graph must change to if it turns out wrong — regardless of which route it takes.

   A decision the work depends on that you cannot settle is a halt: name it and stop. Ask the user only where it blocks finishing at all.

5. **Wire what you mint.**
   A node that is created but not connected has been dumped, not decomposed.
   - Title every task with a brief, descriptive, verb-led imperative (e.g. `Implement X`, `Verify Y`). Never put a person's name in a title or filename — assignment belongs in `assigned_to`.
   - Parent each node to the objective it decomposes. Never unparented, never a catch-all.
   - **Parent/child is already an edge:** Setting `parent_id` establishes hierarchy; do not wire redundant edges between siblings or descendants under the same parent without specific interactions.
   - `depends_on` for true hard blockers, `soft_depends_on` for context-only relations, `contributes_to` with a verbal `stated_weight` and one sentence of justification. Test which: ask what happens if the dependency never completes — impossible or wrong output is hard, still valid but less-informed is soft.
   - Densify with `[[wikilinks]]` to neighbours you confirmed by opening. **The graph should come out denser, not just longer.**
   - Where existing unparented or misparented tasks already cover part of the expansion, adopt them (`pkb__batch_reparent`) rather than minting duplicate siblings.
   - Mint slugged, human-readable IDs upfront (`id: "aops_<slug>"`), not auto-generated ones.
   - Where the expansion forks into parallel tracks that must reconverge, wire an explicit convergence node depending on all of them — an unmerged fork is left unfinished, not decomposed.
   - Where a node unblocks judgment-only work, wire it forward to an explicit follow-up node or owner — an unblock with no successor is a dead end nobody returns to.
   - At least one node in the expansion must be immediately actionable, not gated behind a probe or a SURFACE decision.

6. **Write each body to this shape, and nothing else.**

   ```markdown
   ## Goal — every outcome this component must produce, numbered, one imperative per outcome

   ## Known fragments — [[id]] of a note or document the executor must open + ≤1 clause on why; never a task; where a starting set exists

   ## Not included — bare directives, one clause each, no rationale; where a real collision risk exists
   ```

   Every line must be immediately useful to the agent that executes this component. Nothing whose subject is the component itself: no section defending the scope, naming the stage it sits at, warning what happens if it is read wider, or describing its relation to a sibling. Those relations are the edges you wired in step 5; a prose copy of an edge drifts while the edge stays correct. A qualifier a heading already carries is not restated beneath it.

   Invoke the `craft` skill for the standard these bodies must meet.

## Output

Return the shape of the expansion, not its contents:

```
- Expanded [PARENT-ID] into N components, F forks, P probes
- [TASK-ID] - [TITLE] (fork: <branch> | probe for: <fork-id> | -)
... [ repeat ]
- Halted on: <what you could not settle>   [where applicable]
```

Your verification notes and the reasoning behind each fork go in your reply to the caller, never in a task body.

## Must NOT

- Do not create standalone "decision" tasks or file questions as tasks. Model choices as mutually exclusive option nodes and unknowns as probes.
- Do not put a person's name in titles or filenames (no `nic: ...`); assignment belongs in `assigned_to`.
- Do not prescribe method. An abstract component says what, never how.
- Do not expand into implementation steps: those come from projecting a component through a composed process, which is a later stage.
- Do not compose process or select templates.
- Do not write acceptance criteria or release anything for dispatch.
- Do not originate `intent` or `priority` bands; strategic importance travels on `contributes_to` edges.
