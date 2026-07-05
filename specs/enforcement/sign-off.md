---
id: enforcement-sign-off
title: Enforcement — Sign-off (Layer 4)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification, sign-off, review]
---

# Enforcement — Sign-off (Layer 4)

## Layer 4 — Sign-off

The final review and approval over the workflow as a whole unit.

**Surface-agnostic.** A PR merge is one instantiation, not the definition: not
all work ships through GitHub — a peer review, for example, goes out by email or
web form. Sign-off binds to whatever the delivery surface is.

**Independent of in-workflow review.** A workflow may carry review inside it and
still require a final review over the whole unit.

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
