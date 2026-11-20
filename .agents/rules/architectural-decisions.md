---
trigger: always_on
description: ADRs in specs/decisions/ as NNNN-slug.md; sync INDEX.md and specs/.
---

## Architectural decisions

- Store ADRs in `specs/decisions/` via `/madr` (`status`, `date`, `decision-makers`), named `NNNN-<slug>.md` (kebab-case, no personal names).
- Sync `specs/decisions/INDEX.md` on commit and superseded `specs/` in same PR.
