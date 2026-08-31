---
name: extrapolate
type: command
description: Stage 4 Projection — project one or more abstract components through a woven constellation to yield each one's concrete, ordered obligation set. Also invoked as /project. Produces steps, not tasks.
allowed-tools: [Skill, Read, Grep, Glob, Bash, mcp__services__pkb__get_task, mcp__services__pkb__get_document, mcp__services__pkb__search]
---

# /extrapolate — Project components through the constellation

Also invoked as `/project`.

Take one or more abstract components and run each through a woven constellation of process. The result, per component, is the concrete ordered set of obligations that component actually incurs: which steps it reaches, which it skips, which gates apply to it, and what the constellation does not cover.

You produce obligations, not tasks. Nothing here is cut into dispatchable units, given acceptance criteria, or released.

## Workflow

1. **Take one component at a time.**
   A projection is per-component. Components that share a spine still diverge on which of its steps they reach.

2. **Walk the component through the spine.**
   Instantiate each template step against this component's specifics. Three outcomes per step, and each is recorded:
   - **Reached** — the step applies; state what it means for this component.
   - **Not reached** — the component never enters that branch; say why, so a reviewer can check the skip.
   - **Uncovered** — the component needs work the constellation names nowhere. Record it as a gap in the process, not as an improvised step.

3. **Apply the gates the constellation clipped on.**
   A gate that the composed process attached applies unless the component demonstrably never crosses the door it guards. Weakening a gate at projection time is not available: if the rung is wrong, that is a composition finding, returned upstream.

4. **Sort each obligation by who discharges it.**
   - **Executor-internal** — steps the worker performs. These become the ordered checklist.
   - **Review obligations** — anything that must block acceptance. These are recorded separately, because they are discharged by someone other than the executor and become criteria at the next stage.

5. **Return forks upstream rather than deciding them.**
   Where the projection reveals a decision branch the abstract graph missed, name it and hand it back for decomposition. Choosing one arm here silently converts an open question into a fact.

## Output

Per component:

```
Component: [ID] - [TITLE]
  steps (executor):      1. ... 2. ... 3. ...
  review obligations:    <obligation> — rung: verification|qa|outbound|approval
  not reached:           <step> — <why>
  uncovered:             <what the constellation does not name>   [where applicable]
  forks returned:        <decision branch> — <the arms>           [where applicable]
```

## Must NOT

- Do not cut work into dispatchable units, write task bodies, set status, or write acceptance criteria.
- Do not re-derive or re-select the process. The constellation is an input; a problem with it is a finding returned upstream, not an edit made here.
- Do not resolve a fork the projection uncovers.
- Do not improvise a step to cover a gap. An uncovered obligation is reported as uncovered.
