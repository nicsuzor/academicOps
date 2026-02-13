---
id: base-qa
category: base
---

# Base: Quality Assurance

**Composable base pattern.** Used by QA, critic, and verification workflows.

## Pattern

1. **Lock criteria**: Define success criteria BEFORE examining evidence
2. **Gather evidence**: Observe, test, or review (don't interpret yet)
3. **Evaluate**: Compare evidence against locked criteria
4. **Verdict**: PASS | FAIL | ESCALATE (with evidence citations)

## Key Principle

**Criteria before evidence.** Shifting goalposts invalidates QA. Lock criteria first, then gather evidence, then judge.

## Verdict Format

Always emit structured verdict:

- **PASS**: All criteria satisfied, cite evidence
- **FAIL**: Criteria not met, cite specific gaps
- **ESCALATE**: Cannot determine with available evidence/expertise

## When to Skip

- Trivial changes (typo fixes)
- User explicitly waives verification
