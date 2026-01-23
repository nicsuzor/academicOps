---
id: framework-change
category: governance
bases: [base-task-tracking]
---

# Framework Change

Governance modifications requiring justification and escalation.

## Routing Signals

Modifying:
- AXIOMS.md, HEURISTICS.md
- enforcement-map.md
- hooks/*.py
- settings.json deny rules

## NOT This Workflow

- User data, session artifacts, task updates → standard workflows
- Non-governance code → [[design]]

## Unique Steps

1. Load context: AXIOMS, HEURISTICS, enforcement-map
2. Search prior art
3. Emit structured justification
4. Route for approval (see escalation)
5. CHECKPOINT: Wait for approval
6. Make change exactly as justified
7. Update enforcement-map.md

## Escalation Matrix

| Change Type | Escalation |
|-------------|------------|
| Corollary to existing | auto |
| New heuristic | critic |
| New axiom | human |
| Enforcement hook | critic |
| Deny rule | human |
