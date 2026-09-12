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
   - **Idempotency**: Search the graph before minting. Update existing tasks rather than creating duplicates.
5. **Wire the graph**:
   - Use verb-led imperative titles (e.g. `Implement X`, `Verify Y`). Exclude personal names.
   - Set `parent_id` to establish hierarchy; avoid redundant sibling edges.
   - Use `depends_on` for hard blockers and `soft_depends_on` for informational context.
   - Wire explicit convergence nodes where parallel forks rejoin.
   - Assign slugged human-readable IDs (`id: "aops_<slug>"`).
6. **Task body schema**:

   ```markdown
   ## Goal -- numbered imperative outcomes

   ## Known fragments -- [[id]] notes/docs with rationale

   ## Not included -- out-of-scope boundaries to prevent collisions
   ```

## Output Schema

```
- Expanded [PARENT-ID] into N components, F forks, P probes
- [TASK-ID] - [TITLE] (fork: <branch> | probe for: <fork-id> | -)
- Halted on: <unresolved blocker> [if applicable]
```

## Constraints

- Define abstract outcomes, not execution methods or implementation scripts.
- Do not create standalone "decision" tasks; use mutually exclusive option branches or probes.
- Do not write acceptance criteria or release tasks for dispatch (handled by `brief`).
