---
id: develop-specification
type: template
description: Collaboratively develop a complete task/feature specification before implementation begins
---

# Process: Develop Specification

**When**: automating a manual process, or a good automation/build candidate has
been identified. Purpose: a complete spec before implementation starts —
implementation without this template first is scope-creep waiting to happen.

## One branch, one PR

- Stage 1 opens a **draft** PR into the base branch carrying the spec or design, and its review verdict is recorded on that PR. Stage 1 never merges on its own.
- Stage 2 builds on Stage 1's branch and pushes to the same PR. The spec stays editable on that branch as the build teaches more.
- Stage 2 marks the PR ready for review once the feature is written. That flip does not wait for approval: approval comes at the full review, and spec and feature merge together.

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
12. **Finalize and submit** — open a **draft** PR (`gh pr create --draft`) for review; the spec task never merges on its own. Implementation proceeds on the same branch and PR only after approval (compose [[wf-escalated-approval]] for the go-ahead if the spec commits to something hard to walk back), with the spec still editable; mark the draft PR ready for review (`gh pr ready`) once the feature is written, without waiting for approval; spec and feature merge together after full review.

## Verification before proceeding to implementation

Acceptance criteria section complete; each criterion maps to its test where
code executes, or to its verification otherwise; criteria confirmed on the record to define "done".
