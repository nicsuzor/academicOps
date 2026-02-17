---
id: qa
category: quality-assurance
bases: [base-task-tracking, base-qa, base-handover]
---

# QA

Quality assurance and verification workflows. Multiple modes for different verification needs.

## Routing Signals

- Feature complete, before final commit
- User-facing functionality changes
- Complex changes with acceptance criteria
- Building QA infrastructure
- Framework integration validation

## NOT This Workflow

- Code review / skeptical review → [[critic]]
- Bug investigation → [[debugging]]
- Trivial changes (typo fixes)

---

## Mode Selection

| Mode                       | When to Use                                    | Reference                      |
| -------------------------- | ---------------------------------------------- | ------------------------------ |
| **Quick Verification**     | Pre-completion sanity check, tests pass        | [[quick-verification]]         |
| **Acceptance Testing**     | End-to-end testing, user perspective           | [[acceptance-testing]]         |
| **Qualitative Assessment** | Fitness-for-purpose, UX quality, design intent | [[qualitative-assessment]]     |
| **Integration Validation** | Framework changes, structural verification     | [[integration-validation]]     |
| **System Design**          | Build QA infrastructure for a project          | [[system-design-qa]]           |

## Quick Reference

### Default: Quick Verification

```
Task(subagent_type="qa",
     prompt="Verify work meets acceptance criteria: [CRITERIA].")
```

**Verdicts**: VERIFIED (proceed) or ISSUES (fix and re-verify)

### Qualitative Assessment

```
Task(subagent_type="qa",
     prompt="Qualitative assessment of [FEATURE] against user stories.
     Inhabit the user persona. Is this good for who it was designed for?")
```

**Output**: Narrative prose evaluation, not pass/fail tables.

### Integration Validation

```
Task(subagent_type="qa",
     prompt="Validate framework integration: [FEATURE]. Capture baseline, execute, verify, report evidence.")
```

**Output**: Evidence table (expected vs actual).

## Cross-Client Robustness

AcademicOps supports multiple AI clients. Verify:

- Environment variables from one client don't break another
- Instructions are tailored to active client
- Tool output schemas are robust across client versions
