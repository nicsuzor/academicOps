---
id: critic-detailed
category: quality-assurance
bases: []
---

# Critic Detailed

Full skeptical review. Escalation from critic-fast or direct for complex work.

## Routing Signals

- Framework changes
- Architectural decisions
- Multi-file refactors
- Test code modifications
- ESCALATE from critic-fast

## Invocation

```
Task(subagent_type="critic", model="opus",
     prompt="Review for errors, hidden assumptions, missing verification: [PLAN]. Return: PROCEED | REVISE | HALT")
```

## Verdicts

- **PROCEED**: Execute as planned
- **REVISE**: Apply critic's changes, then execute
- **HALT**: Stop, present issue to user

## Test Code Checks (H37)

When reviewing test code, also check:

- Volkswagen patterns (keyword matching instead of semantic verification)
- Can test pass on wrong behavior?
- Real fixtures vs contrived examples?
