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
4. **Acceptance criteria** — defined with the principal perspective, including a persona paragraph and any
   qualitative dimensions, not just mechanical checks.
5. **Scope** — propose initial scope, explicitly define boundaries (what's out).
6. **Dependencies** — required infrastructure/data; document error handling.
7. **Test and verification design** — for code that executes, an integration
   test that validates each criterion it serves and detects each failure mode;
   for any other criterion, how it is verified.
8. **Implementation approach** — components, data flow, risk assessment.
9. **Effort and risk** — estimates, mitigation plans.
10. **Rule-compliance review** — verify the draft specification against framework
    axioms and rules (proportionality, single source of truth, closure) before
    review. Resolve any required changes before advancing.
11. **Review** — record the full summary review on the record for review.
12. **Finalize and submit** — open a draft PR for review; implementation
    proceeds on the same branch and PR. Once the implementation's code step
    completes, mark the draft PR ready for review without waiting for
    approval (compose [[wf-escalated-approval]] for the go-ahead if the spec
    commits to something hard to walk back).

## Verification before proceeding to implementation

Acceptance criteria section complete; each criterion maps to its test where
code executes, or to its verification otherwise; criteria confirmed on the record to define "done".
