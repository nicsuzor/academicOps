---
name: decompose
type: command
description: Expand one situated objective into an abstract graph of sub-objectives, decision branches, implied prerequisites, and alternate paths, each a node bound to no executor. Use as soon as an objective is on the graph, so other objectives' tasks can intersect with its parts; the PKB custodian (Pauli) runs it. Exclude for direction across the whole graph (use strategize) or writing one node's dispatchable task (use reify).
---

# /decompose -- Expand an objective into an abstract graph

**Object: one objective.** Produce its sub-objectives, forks, and probes with their edges: nodes stating what must become true, bound to no executor, workflow, or repository plan file. Decompose early so other objectives can intersect with these parts; expand only as far as reliable inference reaches and stop at the first unknown. The PKB custodian (Pauli) runs this skill.

State what needs doing, never how. Decompose reads and runs nothing; what the record cannot settle becomes a probe on the graph.

## Workflow

1. **Reconnaissance**: Read the artefacts and search the graph via `ida:hydrate` for how the relevant domain or system already works.
   - List what is settled before naming any unknown; settled facts and answered questions are not nodes or probes.
   - Record each load-bearing premise (whose falsity would change which nodes or forks exist), what settled it, and what it showed; halt and report if any load-bearing premise is false.
   - Verify every pointer between artefacts and the graph both ways; any broken pointer is a finding.
2. **Ground in existing means**:
   - Pull the stage skeleton for this class of work from the workflow template library (`/workflow-library preview`) at stage depth. Place the objective against each stage (met, partly met, or open); any stage requiring a choice (method, frame, venue) becomes a fork, never a pre-chosen step.
   - **Capabilities**: For each component, name required tools, services, data, and credentials and check the record. Ground on recorded working capabilities; add a prerequisite node when absent or refused everywhere; mint a probe wired via `needs: [<probe_id>]` when unrecorded (writing its finding back as a capability record). Defer executor assignment to `/reify`.
3. **Expand within reliable inference**:
   - **Objective altitude**: Keep nodes at objective level bounded to shipping the deliverable and informing the user -- never mechanisms, tool-flag probes, or post-release user installation.
   - **Candidate options & stop rule**: Keep competing candidate options and evaluation criteria inside the scoping task or ADR body until chosen; when chosen, reify only the selected option under `parent: <scoping_task_id>`. Separate decision points from validation nodes. Stop modelling where the next step depends on an unresolved unknown.
4. **Resolve unknowns**:
   - **Decide**: Choose the obvious path and record the rationale in one bullet.
   - **Defer**: Mint an empirical probe task (`classification: probe`) and wire dependent nodes via `needs: [<probe_id>]`.
   - **Surface**: When interactive with the user, surface forks one per turn strictly when the user explicitly reserved that choice prior to action (or an invariant boundary applies); where directed work delegates or implies the choice, evaluate alternatives and select the recommended branch directly without holding downstream work. Reify only the selected branch under `parent: <scoping_task_id>` (`needs` for downstream tasks).
5. **Collapse and merge before minting**:
   - **Collapse to session units**: Combine two components one worker would execute in one session against the same material into one node, unless they must run separately (review, verification, merge), wait on external approval, or choosing one alters the other.
   - **Merge into existing work**: Search the graph via `ida:hydrate` (`done` tasks and templates included) and extend overlapping nodes instead of minting siblings. Trim candidates overlapping completed work to what remains unanswered, linking context with `[[wikilinks]]` under `## Pointers`; mint nothing if nothing remains. A node's first execution belongs to that node.
6. **Wire the graph**: Use verb-led titles (`Implement X`), no personal names, slugged IDs (`<slug>`), and edges per the Three-Purpose Taxonomy: `parent` for hierarchy (no redundant descendant edges), `needs: [<task_id>]` for execution prerequisites, zero `serves` edges on decomposed children (`serves` stays exclusively on the parent Strategic Value Carrier pointing strictly to `type: target` nodes), `[[wikilinks]]` under `## Pointers` for context, and a convergence node where forks rejoin.
7. **Write or redraw the plan view**:
   - Select the user-named `plan-view` template, or discover the single `plan-view`-tagged template with `default: true` (halt loudly if missing, untagged, or ambiguous; never hardcode template IDs).
   - Replace any existing `## Plan` section on the objective's top-level task with the stage strip, Mermaid dependency flowchart, workflow template colour legend, and descendant summary table -- showing planned process and structural dependencies only (no status, assignee, progress, or metrics).

## Output Schema

```
- Expanded [PARENT-ID] into N components, F forks, P probes; C collapsed, M merged
- Premises: <premise> -- held | false | probe TASK-ID; unresolved pointers: <list | none>
- Capabilities: <need> -- recorded on <executor> | absent | probe TASK-ID
- Plan view: written | redrawn on [PARENT-ID] via <template-slug>
- [TASK-ID] - [TITLE] (fork: <branch> | probe for: <fork-id> | -)
- Merged into [EXISTING-ID]: <candidate> (collapsed | overlap | first run)
- Halted on: <unresolved blocker> [if applicable]
```

## Constraints

- Abstract outcomes only; no execution methods, mechanisms, or scripts.
- Bind no node to an executor or workflow and write no acceptance criteria (deferred to `/reify`).
