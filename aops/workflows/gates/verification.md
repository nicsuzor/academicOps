---
id: verification
kind: gate
category: quality-assurance
description: Lightweight checkpoint — lock acceptance criteria before work, confirm evidence against them before calling anything done
door-type: two-way
stakes: Prevents shifting goalposts and "looks done" declarations on routine, reversible work.
skip-when: Trivial changes (typos, comment fixes) where the cost of checking exceeds the cost of being wrong.
pairs-with: [qa, handover]
recommends: [investigation]
version: 1.0.0
permalink: workflows-gates-verification
---

# Gate: Verification

The cheapest gate in the library. Most process templates compose this by default —
it is the floor, not the ceiling.

## Pattern

1. **Before starting work**, lock in clear, testable acceptance criteria. Write
   them down; don't hold them only in your head.
2. Do the work.
3. **Confirm against the locked criteria** using evidence gathered during work
   (tests pass, behavior observed, output verified) — not against criteria
   reinterpreted after the fact.

## Why this is a gate, not just good practice

Locking criteria _before_ evidence exists is what stops an agent from quietly
redefining "done" to match whatever it produced. The lock is the enforcement
mechanism; the confirmation step is just bookkeeping without it.

## Escalation

If verification reveals issues:

- **Simple fix** → fix and re-verify against the same locked criteria.
- **Complex issue, or criteria turn out to be wrong** → escalate to [[qa]]
  (structured PASS/FAIL/ESCALATE) or [[investigation]] if root cause is unknown.

## Declared stakes

This gate exists for any work where "I think it's done" is not sufficient
evidence — i.e. almost everything except pure information lookups. It does
**not** by itself authorize crossing a one-way door (external release,
irreversible action) — see [[human-approval]] and [[outbound-review]] for that.
