---
id: develop-specification
type: template
kind: process
category: general
description: Collaboratively develop a complete task/feature specification before implementation begins
requires: [task-tracking]
pairs-with: [wf-human-approval]
conflicts: []
version: 1.0.0
permalink: workflows-process-develop-specification
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---
> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

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
7. **Integration test design** — a test that validates EACH acceptance
   criterion and detects EACH failure mode.
8. **Implementation approach** — components, data flow, risk assessment.
9. **Effort and risk** — estimates, mitigation plans.
10. **Review** — full summary review with the user.
11. **Finalize and submit** — open a PR for bazaar review; implementation
    proceeds only after approval (compose [[wf-human-approval]] for the
    go-ahead if the spec commits to something hard to walk back).

## Verification before proceeding to implementation

Acceptance criteria section complete; integration test design maps to each
criterion; user confirms these criteria define "done".
