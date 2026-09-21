---
title: Context Discovery Reference
type: reference
category: ref
permalink: analyst-ref-context-discovery
description: Discover and verify existing models, schemas, and conventions before performing data analysis.
---

# Context Discovery

Read existing project context before taking analytical actions to prevent duplicate models, conflicting conventions, or unaligned questions.

## Sources to inspect

1. **`README.md` (root and directory hierarchy)**: Extract core research questions, current project phase, conventions, and tool dependencies.
2. **`data/README.md` (and subdirectories)**: Identify data provenance, raw schemas, refresh cadence, and known data-quality limitations.
3. **Project overview notes (`data/projects/*.md`)**: Note project goals, historical decisions, blockers, and timelines.
4. **Transformation layer (e.g., `dbt/`)**: Inspect existing models across `staging`, `intermediate`, and `marts`. Review `schema.yml` for field descriptions and tests.
5. **Presentation layer (e.g., `streamlit/`, `manuscript/`)**: Identify existing dashboards, rendered reports, and consumed marts.

## Pre-action discovery summary

Before writing code or models, summarize the context to the user:

- Substantive focus and active research questions.
- Data sources, locations, and access patterns.
- Inventory of existing models by layer (staging, intermediate, marts).
- Transformation and presentation engines in use.
- Ask for user direction on the specific task.

## Ambiguous or incomplete context

- **Empty or unmanaged repository**: Propose scaffolding baseline documentation (`instructions/research-documentation.md`) before running ad-hoc queries.
- **Mature repository**: Adopt existing naming conventions and style patterns over generic defaults.
- **Conflicting patterns**: Clarify with the researcher which pattern is authoritative, then record the decision.
