---
id: qa-demo
category: quality-assurance
---

# QA Verification Demo

Independent end-to-end verification before work completion. QA agent checks that work meets acceptance criteria and quality standards.

## When to Use

- Before completing any feature or bug fix
- After all tests pass but before final commit
- When work affects user-facing functionality
- Complex changes with multiple acceptance criteria

## When NOT to Use

- Trivial changes (typo fixes, comment updates)
- Changes already reviewed by user
- Work explicitly marked as draft/WIP
- Emergency hotfixes (but note QA was skipped)

## Scope Signals

| Signal | Indicates |
|--------|-----------|
| Feature complete, tests pass | Ready for QA |
| User-facing change | QA required |
| "Verify before commit" | QA workflow |

## Key Steps

1. Gather work context (request, acceptance criteria, changes made)
2. Invoke QA verifier agent with full context
3. Analyze verdict (VERIFIED or ISSUES)
4. Fix critical/major issues if needed
5. Re-verify if fixes made

## Verification Dimensions

| Dimension | Question |
|-----------|----------|
| **Functionality** | Does it do what was requested? |
| **Quality** | Does it meet code standards? |
| **Completeness** | Are all criteria met? |

## Quality Gates

- QA produces clear VERIFIED or ISSUES verdict
- All three dimensions checked
- Critical/major issues fixed before completion
- No regressions introduced by fixes
