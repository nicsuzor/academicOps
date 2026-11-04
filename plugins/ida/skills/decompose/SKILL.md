---
name: decompose
type: command
description: Expand one situated objective into an abstract graph of sub-objectives, decision branches, implied prerequisites, and alternate paths, each a node bound to no executor. Use as soon as an objective is on the graph, so other objectives' tasks can intersect with its parts; the PKB custodian (Pauli) runs it. Exclude for direction across the whole graph (use strategize) or writing one node's dispatchable task (use reify).
---

# /decompose -- Expand an objective into an abstract graph

**Object: one objective.** The output is its sub-objectives, forks and probes with their edges: nodes that say what must become true, bound to no executor and no workflow. Decompose early, as soon as the objective is captured, because its sub-objectives are what other objectives' tasks intersect with; a task minted elsewhere can only account for them once they exist. Expand only as far as reliable inference reaches now, and stop at the first unknown. The PKB custodian (Pauli) runs this skill.

State what needs doing, never how. Decompose reads; it runs nothing. What the record cannot settle becomes a probe on the graph.

## Workflow

1. **Reconnaissance**: Read the artefacts and the graph.
   - Search the record or knowledge base for how the relevant part of the domain or system already works; list what is settled before naming any unknown. What the record settles is not a node or probe; an unknown the record answers is not a node.
   - A premise is load-bearing when its falsity would change the graph's shape (which nodes exist, which forks are open). Record each one, what settled it, and what it showed.
   - Resolve every pointer between artefacts and graph both ways. One that no longer resolves is a finding.
   - A false load-bearing premise halts the run: record it and stop.
2. **Ground in existing means**:
   - Take the stage skeleton for this class of work from the workflow template library (e.g. `/workflow-library preview`) at stage depth. Its stages are the spine; a stage filled by a choice (method, frame, venue) becomes a fork, never a chosen step.
   - Place the objective against each stage: met, partly met or open, and the node that carries it.
   - **Capabilities.** For each component, name what it needs (tool and operation, service, data, credentials) and settle from the record whether some executor has it. Recorded as working somewhere: ground on it. Recorded as absent or refused everywhere: the component needs a prerequisite node. Not on record: a probe the component `depends_on`, whose finding is written back as a capability record. Which executor runs the component is settled at reification, not here.
3. **Expand within reliable inference**:
   - **Objective altitude**: Nodes are objectives ("clarify X and address gaps if required", "create the workflow for Y"), never mechanisms, choices between mechanisms, or probes of tool flags. Those belong to the worker.
   - Model sub-objectives as far as reliable inference allows. Fork at branching points, one node per alternative. Separate decision points from their validation nodes.
   - **Stop rule**: When the next step depends on something not yet known, the node ends naming that unknown, and no branches beyond it are modelled.
4. **Resolve unknowns**:
   - **Decide**: Choose the obvious path and record the rationale in one bullet.
   - **Defer**: Mint a probe task (`classification: probe`); dependent nodes `depends_on` it.
   - **Surface**: Model genuine trade-offs as mutually exclusive option nodes; choosing one completes it and cancels the rest. With the author in the session, surface forks in conversation, one per turn; mint option nodes only for forks they defer.
5. **Collapse and merge before minting**: mint only what no existing node can carry.
   - **Collapse to session units**: two components one worker would do in one session against the same material are one node, unless the second must not run in that session (review, verification, merge), they are exclusive options, one gates on another party, or deciding between them changes the second.
   - **Merge into what exists**: search the graph first, `done` tasks and templates included; extend an overlapping node instead of minting a sibling. Overlap with completed work cuts the candidate to what that work left unanswered, wired `soft_depends_on` it; if nothing is left, do not mint.
   - **A first run is not a step**: the first execution of an existing node belongs to that node.
6. **Wire the graph**: verb-led titles (`Implement X`), no personal names; `parent_id` for hierarchy, no redundant sibling edges; `depends_on` for hard blockers, `soft_depends_on` for informing context; a convergence node where forks rejoin; slugged ids (`<slug>`).
7. **Write or redraw the plan view**:
   - **Template selection**: Apply the plan-view template named by the user, if specified. Otherwise, discover templates tagged `plan-view` and select the template whose frontmatter marks `default: true`. Do not hardcode template names or identifiers in instructions. Halt loudly if the named template is missing, if no template carries the `plan-view` tag, or if multiple templates carry `default: true`.
   - **Render the plan**: Apply the selected template to write a `## Plan` section on the objective's top-level task containing the stage strip, Mermaid dependency flowchart, workflow template colour legend, and summary table derived from descendant tasks. Display planned process and structural dependencies only; omit task status, assignee, progress, and execution metrics to preserve single source of truth on the tasks.
   - **Idempotent redrawing**: Each run and re-run completely replaces any existing `## Plan` section in place, carrying added detail, forks, and graph modifications from the current tree.

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
- Bind no node to an executor or a workflow and write no acceptance criteria: a node is reified (`/reify`) when it is next to run, and not before.
- Plan view shows planned process structure only; task status stays exclusively on child tasks.
