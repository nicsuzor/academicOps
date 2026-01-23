---
id: critic-fast
category: quality-assurance
bases: []
---

# Critic Fast

Quick sanity check. Default critic invocation.

## Routing Signals

- Routine plans, standard file modifications
- Single-domain changes

## NOT This Workflow

- Research projects → [[critic-detailed]]
- High risk / high value work → [[critic-detailed]]

## Invocation

```
Task(subagent_type="critic", model="haiku",
     prompt="Quick sanity check: [PLAN]. Check scope creep, missing requirements, obvious errors. Return: PROCEED | ESCALATE | HALT")
```

## Verdicts

- **PROCEED**: Execute as planned
- **ESCALATE**: Re-invoke with [[critic-detailed]]
- **HALT**: Stop, present issue to user
