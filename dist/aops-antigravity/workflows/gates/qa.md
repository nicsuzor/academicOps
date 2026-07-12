---
id: qa
kind: gate
category: quality-assurance
description: Structured QA obligation — lock criteria, gather evidence, judge, emit PASS/FAIL/ESCALATE — with modes for how deep to go
door-type: two-way
stakes: Feature-complete or user-facing changes proceeding without independent evidence that they work.
skip-when: Trivial changes, or user explicitly waives verification for this artifact.
requires: []
pairs-with: [outbound-review, handover]
conflicts: []
version: 2.0.0
permalink: workflows-gates-qa
---

# Gate: QA

The general-purpose QA obligation. [[verification]] is the floor (lock/confirm);
this gate adds a structured verdict and depth-of-review modes for when more
than a sanity check is warranted.

## Core Pattern

1. **Lock criteria** — define success criteria BEFORE examining evidence.
2. **Gather evidence** — observe, test, or review. Don't interpret yet.
3. **Evaluate** — compare evidence against the locked criteria.
4. **Verdict** — `PASS` | `FAIL` | `ESCALATE`, with evidence citations.

**Criteria before evidence** is the load-bearing rule: shifting goalposts after
seeing the output invalidates the QA pass.

## Depth Modes

| Mode                       | When                                                  | What it produces                        |
| -------------------------- | ----------------------------------------------------- | --------------------------------------- |
| **Quick verification**     | Pre-completion sanity check, tests pass               | VERIFIED / ISSUES                       |
| **Acceptance testing**     | End-to-end, from the user's perspective               | Evidence table (expected vs actual)     |
| **Qualitative assessment** | Fitness-for-purpose, UX quality, design intent        | Narrative prose evaluation, not a table |
| **Integration validation** | Framework/structural changes, cross-client robustness | Evidence table + regression check       |

Pick the shallowest mode that would actually catch the failure mode you're
worried about — depth is proportionate to stakes, not a default maximum.

## Routing signals

- Feature complete, before final commit
- User-facing functionality changed
- Complex changes with non-obvious acceptance criteria
- Framework/infrastructure changes needing cross-client checks

**NOT this gate**: bug investigation with unknown cause → [[investigation]].

## When to Skip

- Trivial changes (typo fixes)
- User explicitly waives verification

## Declared stakes

Door-type is two-way (a FAIL sends work back for another pass; it doesn't itself
authorize an irreversible release). When the artifact under review is about to
leave the team, compose [[outbound-review]] instead of, or in addition to, this
gate — QA judges correctness, outbound-review judges fitness-to-ship.
