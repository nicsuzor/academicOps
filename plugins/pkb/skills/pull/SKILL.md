---
name: pull
description: Claim a queued task, execute it, record the result on the task, and hand over.
---

# Pull

Each task was vetted before it became available. Execute it faithfully: it is the whole of your obligation and the limit of your authority.

## 1. Claim

Claim the task by id. That marks it `in_progress`, assigns it to you, and returns its full requirements. If you were given no id, search for the task; if you cannot find it, halt and report.

**Check the status is `queued` before you execute.** Anything else means it is not ready — halt and report.

The claimed task is your unit of delivery, children included. Existing children are input to your plan: execute them directly in sequence or in parallel where the work allows. The return contract attaches to the **claimed** task — one deliverable, with evidence and an output URL — never a spray of per-child deliverables.

## 2. Plan

Track every step and deliverable on your native task list, including all outstanding subtasks, then a verification step, and finally "Handover".

## 3. Execute

Execute the steps systematically, sequencing in parallel where the work allows.

**Refuse and attempt.** Refuse any choice not derivable with reasonable confidence from the axioms plus the context you were given — that is the same limit on your authority, applied to decisions. Attempt everything that does not depend on a refused choice, then take `dump`'s `partial` path.

## 4. Verify

Check your work against every requirement, and carry the evidence for each into the report you hand back — the brief's evidence bar is what your claims are admitted against. Technical compliance is not sufficient; the bar is excellence. Rectify what falls short, and do not certify a task complete without certainty that it is delivered in full.

## 5. Hand over

Invoke the `dump` skill. It records your work and lets the task proceed; halt without it and the work is destroyed. Take its `full` path when the task is done, `partial` when you refused choices but attempted the rest, and its failure path when you are genuinely blocked.

## Halt conditions

- Any failed check — stop. Do not work around an infrastructure or tooling problem.
- **Non-interactive execution.** In a headless environment, never emit an interactive prompt or wait for input. Every decision path needs an automatic route or a handback at `partial`.
- In every case — complete, partial, or failed — exit through the handover. Do not script around it.
