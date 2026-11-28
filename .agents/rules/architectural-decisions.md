---
trigger: always_on
description: Agents own implementation and sequencing calls; ADRs in specs/decisions/ as NNNN-slug.md; sync INDEX.md and specs/.
---

## Architectural decisions

- Implementation and sequencing choices (build order, which branch or PR work builds on, when to wait on another change) belong to the agents doing the work: decide them, record the reasoning where the work is tracked, and never put them to the user as a question.
- Store ADRs in `specs/decisions/` via `/madr` (`status`, `date`, `decision-makers`), named `NNNN-<slug>.md` (kebab-case, no personal names).
- Sync `specs/decisions/INDEX.md` on commit and superseded `specs/` in same PR.
