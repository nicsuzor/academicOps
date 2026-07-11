---
id: enforcement-sign-off
title: Enforcement — Sign-off (Layer 4)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, sign-off, review]
---

# Enforcement — Sign-off (Layer 4)

> **Numbering note.** `Layer 4` here belongs to the **module-boundary layer model** (`Layer 0`–`Layer 4`, spanning [pyramid.md](pyramid.md), [task-contract.md](task-contract.md), [workflow.md](workflow.md), this file) — an axis orthogonal to [`enforcement.md`](enforcement.md)'s pipeline (`L0`–`L11`) and pyramid-position (`L0`–`L7`) numbers. They reuse the same digits for a different purpose; see [enforcement.md § Two views of the same mechanisms](enforcement.md#two-views-of-the-same-mechanisms) for the distinction.

## Layer 4 — Sign-off

The final review and approval over the workflow as a whole unit.

**Surface-agnostic.** A PR merge is one instantiation, not the definition: not
all work ships through GitHub — a peer review, for example, goes out by email or
web form. Sign-off binds to whatever the delivery surface is.

**Independent of in-workflow review.** A workflow may carry review inside it and
still require a final review over the whole unit.

**Same contract, release-unit scale.** The sign-off brief is
[evidence-contract.md](evidence-contract.md) applied to the whole workflow: a
one-page prose brief in which every delivered/checked claim carries a
resolvable pointer (command+output, file:line, resolving URL, quoted source)
or a stated failure reason. A reviewer approving on the strength of the
brief's rhetorical shape rather than checking its claims has not performed
sign-off — see [evidence-contract.md#substance-over-form](evidence-contract.md#substance-over-form).

### Mechanisms (the git PR-pipeline instance)

- **Required reviewers** — `enforcer-status` (axiom review of head) and
  `qa-status` (runtime verification), re-run on each SHA so a state change voids
  stale evidence.
- **`review-attestation`** — fail-closed proof a named reviewer ran on this SHA.
- **`admit-status`** — the human "make it mergeable" decision; sticky across
  pushes.
- **`alignment-status`** — advisory design-intent review, informing the admit
  gate.
- **`comment-triage-status`** — fail-closed over unresolved third-party review
  comments.
- **Branch protection** and **CODEOWNERS** — AND-gate the required checks and
  auto-request the maintainer. **Lint / Pytest** — mechanical CI floor.
- **Fixers** (informational): `responder` (pre-admission), `mechanic`
  (post-admission dev and conflict resolve), the `@claude` assistant, and the
  `force-review` escape hatch.
