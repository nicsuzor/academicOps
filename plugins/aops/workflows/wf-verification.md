---
alias:
- wf-verification-wf-verification
- wf-verification
created: 2026-07-20T07:23:41.042618480+00:00
id: wf-verification
last_modified: 2026-08-29T00:39:42.434488680+00:00
modified: 2026-08-29T00:39:42.434486466+00:00
permalink: wf-verification
tags:
- wf-template
- v0.4
- module-f
title: wf-verification
type: template
---

## What this step does

Lightweight checkpoint — lock acceptance criteria before work, confirm evidence against them before calling anything done. The cheapest gate in the library. Most process templates compose this by default — it is the floor, not the ceiling.

## Pattern

1. **Before starting work**, lock in clear, testable acceptance criteria. Write them down; don't hold them only in your head.
2. Do the work.
3. **Confirm against the locked criteria** using evidence gathered during work (tests pass, behavior observed, output verified) — not against criteria reinterpreted after the fact.

## Why this is a gate, not just good practice

Locking criteria _before_ evidence exists is what stops an agent from quietly reining "done" to match whatever it produced. The lock is the enforcement mechanism; the confirmation step is just bookkeeping without it.

## Escalation

If verification reveals issues:

- **Simple fix** → fix and re-verify against the same locked criteria.
- **Complex issue, or criteria turn out to be wrong** → escalate to [[wf-qa]] (structured PASS/FAIL/ESCALATE) or [[wf-investigation]] if root cause is unknown.

## Declared stakes

This gate exists for any work where "I think it's done" is not sufficient evidence — i.e. almost everything except pure information lookups. Door-type is two-way: a failed check loops back for a fix against the locked criteria; it does **not** by itself authorize crossing a one-way door (external release, irreversible action) — see [[wf-human-approval]] and [[wf-outbound-review]].

**Skip conditions** (evidence the submission must carry to discharge this gate without a separate review node):

- **Pure read-only queries**: output produces no state mutations or durable artifacts.
- **Deterministic machine proof**: submission includes execution logs or test output that mechanically prove the locked criteria without requiring subjective inspection.
- **Trivial/cosmetic changes**: diff carries zero behavioral, structural, or semantic impact.
