---
name: decompose
type: command
description: Expand one situated objective into an abstract graph of sub-objectives, decision branches, implied prerequisites, and alternate paths. Stops before implementation detail.
---

# /decompose -- Expand an objective into an abstract graph

Expand a situated objective into smaller, abstract components: sub-objectives, decision branches, prerequisites, and alternate paths. State what needs doing, never how.

## Workflow

1. **Reconnaissance**: Inspect codebase, graph, and runtime environment live before decomposing. If a load-bearing premise is invalid, record the finding and halt.
2. **Ground in existing means**: Base components on available capabilities, tools, and real constraints.
3. **Expand within reliable inference**:
   - Model sub-objectives as far as reliable inference allows; stop before implementation details.
   - Fork the graph at branching points, modeling each alternative as a distinct node.
   - Separate decision points from their validation nodes.
4. **Resolve unknowns**:
   - **Decide**: Choose the obvious path and record the rationale in one bullet.
   - **Defer**: Mint an empirical probe task (`classification: probe`) for missing runtime data. Wire dependent nodes to `depends_on` the probe.
   - **Surface**: Model genuine trade-offs as mutually exclusive option nodes. Choosing an option marks it complete and cancels competing options. Never create a standalone "decision" task.
5. **Collapse and merge before minting**: Every surplus node costs a brief, a reconcile pass and reader attention for its whole life, so mint only what no existing node can carry.
   - **Collapse to session units**: Two components one worker would carry out in a single session against the same material are one node. Test: briefed once, would a worker do both without an intervening decision or handover? Keep them apart only where the second must not run in the session that did the first (review, independent verification, merge); where they are mutually exclusive options; where one is a gate on another party; or where deciding between the two changes what the second is.
   - **Merge into what exists**: Search the graph before minting, `done` tasks and workflow templates included. Where a candidate overlaps an existing node, extend that node instead of minting a sibling; mint only for a genuinely new step. Where the overlap is with completed work, cut the candidate down to what that work left unanswered and wire it `soft_depends_on` that work -- if nothing is left, do not mint.
   - **A first run is not a step**: The first execution of an existing node -- a baseline, a first pass of a method already modelled -- belongs to that node, not to a new node beside it.
6. **Wire the graph**:
   - Use verb-led imperative titles (e.g. `Implement X`, `Verify Y`). Exclude personal names.
   - Set `parent_id` to establish hierarchy; avoid redundant sibling edges.
   - Use `depends_on` for hard blockers and `soft_depends_on` for informational context.
   - Wire explicit convergence nodes where parallel forks rejoin.
   - Assign slugged human-readable IDs (`id: "aops_<slug>"`).

## Output Schema

```
- Expanded [PARENT-ID] into N components, F forks, P probes; C collapsed, M merged into existing nodes
- [TASK-ID] - [TITLE] (fork: <branch> | probe for: <fork-id> | -)
- Merged into [EXISTING-ID]: <candidate> (collapsed | overlap | first run)
- Halted on: <unresolved blocker> [if applicable]
```

## Constraints

- Define abstract outcomes, not execution methods or implementation scripts.
- Do not create standalone "decision" tasks; use mutually exclusive option branches or probes.
- Do not mint a node where an existing one can carry the work; report the merge instead.
- Do not write acceptance criteria or release tasks for dispatch (handled by `brief`).
