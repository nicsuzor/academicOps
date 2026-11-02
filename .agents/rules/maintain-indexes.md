---
trigger: always_on
description: Keep indexes, catalogs, and tables of contents synchronized with canonical source files.
---

## Keep indexes synchronized with their sources

Whenever creating, modifying, renaming, or deleting a file, rule, skill, workflow, or definition that is indexed in a README, catalog, or table of contents, update the index in the same change:

- **Derive directly from canonical source:** Each row or entry (slug, title, description, trigger, or signature) must accurately reflect the canonical metadata or frontmatter in the source file. Do not author divergent summaries or paraphrases.
- **Maintain across all indexes:** This obligation applies generally across the repository (e.g. axiom indexes, rule catalogs, skill tables, workflow registries), not just specific file types.
- **Agentic maintenance over mechanical mirror checks:** Agents maintain documentation accuracy semantically as part of their work. Do not write bespoke generation scripts, linters, or change-detector tests for individual index files.
