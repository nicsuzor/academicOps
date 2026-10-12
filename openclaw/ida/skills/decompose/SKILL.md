---
name: decompose
type: command
description: Expand one situated objective into an abstract graph of sub-objectives, decision branches, implied prerequisites, and alternate paths. Stops before implementation detail.
---

# /decompose -- Expand an objective into an abstract graph

State what needs doing, never how.

## Workflow

1. **Reconnaissance**: Inspect the artefacts, the graph and the runtime live before decomposing.
   - A premise is load-bearing when its falsity would change the graph's shape (which nodes exist, which forks are open). Check each one; record what was checked and what it showed.
   - Resolve every pointer between artefacts and graph both ways. One that no longer resolves is a finding.
   - A false load-bearing premise halts the run: record it and stop. One that cannot be checked becomes a probe (step 4).
2. **Ground in existing means**: Base components on available capabilities, tools, and real constraints.
   - Take the stage skeleton for this class of work from `/workflow-library preview` at stage depth (on a bus, send the ask whole to the PKB session). Its stages are the spine; a stage filled by a choice (method, analytical frame, venue) becomes a fork in step 3, never a chosen step.
3. **Expand within reliable inference**:
   - Model sub-objectives as far as reliable inference allows; stop before implementation details.
   - Fork the graph at branching points, modeling each alternative as a distinct node.
   - Separate decision points from their validation nodes.
4. **Resolve unknowns**:
   - **Decide**: Choose the obvious path and record the rationale in one bullet.
   - **Defer**: Mint a probe task (`classification: probe`) for missing runtime data; dependent nodes `depends_on` it.
   - **Surface**: Model genuine trade-offs as mutually exclusive option nodes. Choosing an option marks it complete and cancels competing options. When the author is in the session, surface forks in conversation, one per turn, and take their answer before the next; mint option nodes only for forks they defer.
5. **Collapse and merge before minting**: mint only what no existing node can carry; every surplus node costs a brief, a reconcile pass and attention for its whole life.
   - **Collapse to session units**: Two components one worker would do in one session against the same material are one node. Test: briefed once, would a worker do both without an intervening decision or handover? Keep them apart only where the second must not run in the session that did the first (review, verification, merge); where they are exclusive options; where one gates on another party; or where deciding between them changes what the second is.
   - **Merge into what exists**: Search the graph before minting, `done` tasks and workflow templates included. Extend an overlapping node instead of minting a sibling. Where the overlap is with completed work, cut the candidate to what that work left unanswered and wire it `soft_depends_on` that work; if nothing is left, do not mint.
   - **A first run is not a step**: The first execution of an existing node (a baseline, a first pass of a modelled method) belongs to that node, not a new one.
6. **Wire the graph**:
   - Use verb-led imperative titles (`Implement X`, `Verify Y`); no personal names.
   - Set `parent_id` to establish hierarchy; avoid redundant sibling edges.
   - Use `depends_on` for hard blockers and `soft_depends_on` for informational context.
   - Wire explicit convergence nodes where parallel forks rejoin.
   - Assign slugged human-readable IDs (`id: "aops_<slug>"`).

## Output Schema

```
- Expanded [PARENT-ID] into N components, F forks, P probes; C collapsed, M merged
- Premises: <premise> -- held | false | probe TASK-ID; unresolved pointers: <list | none>
- [TASK-ID] - [TITLE] (fork: <branch> | probe for: <fork-id> | -)
- Merged into [EXISTING-ID]: <candidate> (collapsed | overlap | first run)
- Halted on: <unresolved blocker> [if applicable]
```

## Constraints

- Abstract outcomes only; no execution methods or scripts.
- Do not write acceptance criteria or release tasks for dispatch (handled by `/reify`).
