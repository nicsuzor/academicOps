---
name: decompose
type: command
description: Expand one situated objective into an abstract graph of sub-objectives, decision branches, implied prerequisites, and alternate paths. Stops before implementation detail.
---

# /decompose -- Expand an objective into an abstract graph

State what needs doing, never how. Decompose reads; it runs nothing. What the record cannot settle becomes a probe on the graph.

## Workflow

1. **Reconnaissance**: Read the artefacts and the graph.
   - A premise is load-bearing when its falsity would change the graph's shape (which nodes exist, which forks are open). Record each one, what settled it, and what it showed.
   - Resolve every pointer between artefacts and graph both ways. One that no longer resolves is a finding.
   - A false load-bearing premise halts the run: record it and stop.
2. **Ground in existing means**:
   - Take the stage skeleton for this class of work from `/workflow-library preview` at stage depth (on a bus, send the ask whole to the PKB session). Its stages are the spine; a stage filled by a choice (method, frame, venue) becomes a fork, never a chosen step.
   - Place the objective against each stage: met, partly met or open, and the node that carries it.
   - **Capabilities.** For each component, name what it needs (tool and operation, service, data, credentials) and the executor that will run it, and settle each from the record. Recorded as working there: ground on it. Recorded as absent or refused there: the component needs another executor or a prerequisite node. Not on record: a probe the component `depends_on`, whose finding is written back as a capability record.
3. **Expand within reliable inference**: model sub-objectives as far as reliable inference allows, stopping before implementation. Fork at branching points, one node per alternative. Separate decision points from their validation nodes.
4. **Resolve unknowns**:
   - **Decide**: Choose the obvious path and record the rationale in one bullet.
   - **Defer**: Mint a probe task (`classification: probe`); dependent nodes `depends_on` it.
   - **Surface**: Model genuine trade-offs as mutually exclusive option nodes; choosing one completes it and cancels the rest. With the author in the session, surface forks in conversation, one per turn; mint option nodes only for forks they defer.
5. **Collapse and merge before minting**: mint only what no existing node can carry.
   - **Collapse to session units**: two components one worker would do in one session against the same material are one node, unless the second must not run in that session (review, verification, merge), they are exclusive options, one gates on another party, or deciding between them changes the second.
   - **Merge into what exists**: search the graph first, `done` tasks and templates included; extend an overlapping node instead of minting a sibling. Overlap with completed work cuts the candidate to what that work left unanswered, wired `soft_depends_on` it; if nothing is left, do not mint.
   - **A first run is not a step**: the first execution of an existing node belongs to that node.
6. **Wire the graph**: verb-led titles (`Implement X`), no personal names; `parent_id` for hierarchy, no redundant sibling edges; `depends_on` for hard blockers, `soft_depends_on` for informing context; a convergence node where forks rejoin; slugged ids (`aops_<slug>`).

## Output Schema

```
- Expanded [PARENT-ID] into N components, F forks, P probes; C collapsed, M merged
- Premises: <premise> -- held | false | probe TASK-ID; unresolved pointers: <list | none>
- Capabilities: <need> on <executor> -- recorded | absent | probe TASK-ID
- [TASK-ID] - [TITLE] (fork: <branch> | probe for: <fork-id> | -)
- Merged into [EXISTING-ID]: <candidate> (collapsed | overlap | first run)
- Halted on: <unresolved blocker> [if applicable]
```

## Constraints

- Abstract outcomes only; no execution methods or scripts.
- Do not write acceptance criteria or release tasks for dispatch (handled by `/reify`).
