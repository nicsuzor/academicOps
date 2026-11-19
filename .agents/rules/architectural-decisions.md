---
trigger: always_on
description: Architectural decisions live in specs/decisions/, follow NNNN-slug.md naming, and synchronize specs/decisions/INDEX.md atomically.
---

## Architectural Decision Records

Significant architectural decisions are recorded using the minimal Markdown Architectural Decision Records (MADR) format from the `/madr` skill with repository-local metadata and synchronization:

- **Location**: Store records in `specs/decisions/` formatted with the minimal MADR template from `/madr` plus YAML frontmatter (`status`, `date`, `decision-makers`).
- **Naming**: Filenames follow `NNNN-<slug>.md` (e.g. `0001-use-madr-for-architectural-decisions.md`) with a 4-digit sequential prefix and an active-imperative kebab-case slug. Personal names and persona prefixes are strictly prohibited.
- **Index Synchronization**: `specs/decisions/INDEX.md` must be updated in the same commit whenever an ADR is created, modified, deprecated, or superseded.
- **Specification Alignment**: Subsystem specifications (`specs/`) define target behavior and state only, carrying zero historical deliberations. When a new ADR supersedes an existing decision, any affected subsystem specifications in `specs/` must be updated in the same PR.
