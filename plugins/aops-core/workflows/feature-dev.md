---
id: feature-dev
type: template
kind: process
category: development
description: Test-first feature development from idea to ship — "add feature X", "build Y", "fix bug Z" with a known cause
requires: [task-tracking, tdd]
pairs-with: [wf-verification, wf-handover]
conflicts: []
recommends: []
version: 1.1.0
permalink: workflows-process-feature-dev
---

# Process: Feature Development

**When to invoke**: user says "add feature X", "build Y", "implement Z", or a
bug with a known cause and a clear fix. Unknown-cause bugs route to
[[investigation]] first.

## Steps

1. **Understand requirements** — identify features, UX, constraints.
2. **Propose plan** — a concise implementation summary. Before finalising,
   surface any observation that could be read as a design choice (unexpected
   constraint, ambiguous behaviour, unstated requirement) — surface the
   observation, not your interpretation of it, to the user.
3. **Draft tests** — compose [[tdd]], first behavior before implementation.
4. **Implement** — red-green-refactor.
5. **Verify** — compose [[wf-verification]] against the original request, not
   just the tests.
6. **Submit PR** — compose [[wf-handover]].

## Critical Rules

- Test-first, always.
- Minimal implementation — only what the tests require.
- Refactor without breaking green tests.
- Validate against the original goal, not just the test suite.
- No reverts unless changes cause errors.

## NOT this template

- Cause-unknown bugs → [[investigation]], then feature-dev once cause is known.
