---
id: develop-specification
type: template
description: Collaboratively develop a complete task/feature specification before implementation begins
---

# Process: Develop Specification

**When**: automating a manual process, or a good automation/build candidate has
been identified. Purpose: a complete spec before implementation starts —
implementation without this template first is scope-creep waiting to happen.

## Steps

1. **Identify the target** — confirm a manual process worth automating, or a
   feature worth specifying.
2. **Create the spec document** from the standard template.
3. **Problem statement** — collaborative: what, why, for whom.
4. **Acceptance criteria** — user-owned, including a persona paragraph and any
   qualitative dimensions, not just mechanical checks.
5. **Scope** — propose initial scope, explicitly define boundaries (what's out).
6. **Dependencies** — required infrastructure/data; document error handling.
7. **Test and verification design** — for code that executes, an integration
   test that validates each criterion it serves and detects each failure mode;
   for any other criterion, how it is verified.
8. **Implementation approach** — components, data flow, risk assessment.
9. **Effort and risk** — estimates, mitigation plans.
10. **Review** — full summary review with the user.
11. **Finalize and submit** — open a PR for bazaar review; implementation
    proceeds only after approval (compose [[wf-escalated-approval]] for the
    go-ahead if the spec commits to something hard to walk back).

## Verification before proceeding to implementation

Acceptance criteria section complete; each criterion maps to its test where
code executes, or to its verification otherwise; user confirms these criteria define "done".
