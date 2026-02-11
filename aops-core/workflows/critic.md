---
id: critic
category: quality-assurance
bases: [base-qa]
---

# Critic

Skeptical review of plans and work. Default: quick sanity check. Escalates automatically for complex work.

## Routing Signals

- Before executing a plan
- After completing significant work
- User requests review

## NOT This Workflow

- Verifying feature works → [[qa]]
- Investigating bugs → [[debugging]]

## Default Mode: Fast

Quick sanity check for routine work.

**Signals for fast mode:**

- Routine plans, standard file modifications
- Single-domain changes
- Low-risk changes

**Invocation:**

```
Task(subagent_type="critic", model="haiku",
     prompt="Quick sanity check: [PLAN]. Check scope creep, missing requirements, obvious errors. Return: PROCEED | ESCALATE | HALT")
```

## Escalation Mode: Detailed

Full skeptical review. Triggered automatically or directly for complex work.

**Escalation triggers:**

- Framework changes
- Architectural decisions
- Multi-file refactors
- Test code modifications
- ESCALATE verdict from fast mode
- Research projects
- High risk / high value work

**Invocation:**

```
Task(subagent_type="critic", model="opus",
     prompt="Review for errors, hidden assumptions, missing verification: [PLAN]. Return: PROCEED | REVISE | HALT")
```

## Verdicts

| Verdict | Meaning | Next Step |
|---------|---------|-----------|
| **PROCEED** | Execute as planned | Continue with work |
| **ESCALATE** | Needs deeper review | Re-invoke in detailed mode |
| **REVISE** | Apply critic's changes | Update plan, then execute |
| **HALT** | Serious issue found | Stop, present to user |

## Test Code Checks (H37)

When reviewing test code (detailed mode), also check:

- Volkswagen patterns (keyword matching instead of semantic verification)
- Can test pass on wrong behavior?
- Real fixtures vs contrived examples?

## Escalation Logic

```
if (framework_change OR architectural_decision OR multi_file_refactor OR test_code):
    → detailed mode
elif (fast_mode_verdict == ESCALATE):
    → detailed mode
else:
    → fast mode
```
