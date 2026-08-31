---
title: Principal Sign-off Loop
type: template
category: gate
description: The review-until-approval loop the principal runs at a human sign-off gate before work may be marked done. Select when human sign-off is the recorded review obligation. Not for worker self-certification.
tags: [signoff, approval, principal, governance, loop, gate]
---

# Gate: Principal Sign-off Loop

Governance loop requiring explicit human principal approval before marking critical deliverables complete.

## 1. Primary Material and Evidence Assembly

- Obtain the actual output artifacts and full execution record of `<unit>`.
- Retrieve locked acceptance criteria and verify independent grading evidence.

## 2. Present Evidence Digest (Gate A)

- Present structured digest (`wf-signoff-brief`) to `<principal>`.
- Open with verdict; include verbatim excerpts; end with single open question.
- **Approved by principal** -> Mark work done; loop terminates.
- **Defects confirmed** -> Proceed to step 3.
- **Silence is not consent** -> Work remains unapproved until principal acts.

## 3. Propose Remediation Plan (Gate B)

- If defects were identified, formulate a single consolidated remediation plan:
  - Specific defect description and root cause.
  - Proposed fix and designated worker.
  - Method for verifying fix in the next round.
- Present plan to principal for approval before dispatching workers.

## 4. Dispatch Remediation and Re-Verify

- Execute approved remediation plan.
- Re-verify revised artifact with fresh independent evidence.
- Re-enter loop at step 1 with updated evidence digest.

## Exit Condition

Explicit Gate A approval from the principal.
