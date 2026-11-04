---
trigger: always_on
description: Keep indexes, catalogs, and tables of contents synchronized with canonical source files.
---

## Keep indexes synchronized with their sources

Whenever creating, modifying, renaming, or deleting a file, rule, skill, workflow, or definition that is indexed in a README, catalog, or table of contents, update the index in the same change:

- **Derive directly from canonical source:** Each row or entry (slug, title, description, trigger, or signature) must accurately reflect the canonical metadata or frontmatter in the source file. Do not author divergent summaries or paraphrases.
- **Maintain across all indexes:** This obligation applies generally across the repository (e.g. axiom indexes, rule catalogs, skill tables, workflow registries), not just specific file types.
- **Enforcement map is not a workflow or project-rule catalog:** When editing `specs/ENFORCEMENT-MAP.md`, every row must only reference a specific rule derived from our axioms (`plugins/rbg/skills/axioms/`) and applicable to agents working in any third-party project. Workflows are not rules and do not enforce rules; creating or modifying workflows must not produce token enforcement map rows, as the only applicable rule is "agents must follow workflows given to them" and nothing more than that.
- **Agentic maintenance over mechanical mirror checks:** Agents maintain documentation accuracy semantically as part of their work. Do not write bespoke generation scripts, linters, or change-detector tests for individual index files.
