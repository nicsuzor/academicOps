---
id: context-map-schema
title: context-map.json Schema
type: spec
status: ready
tier: 4
depends_on: [prompt-hydration, taxonomy]
tags: [framework, schema, context, discovery]
---

# context-map.json Schema

Standardised schema for repository self-description used by agents for documentation discovery and context injection.

## Giving Effect

- [[.agents/context-map.json]] - Primary implementation in this repository
- [[aops-core/lib/context_map.py]] - Python library for loading and formatting the map
- [[aops-core/hooks/router.py]] - Consumes the map for lightweight hydration
- [[aops-core/skills/project/workflows/context-map-audit.md]] - Workflow for maintaining the map

## Purpose

The `context-map.json` is a machine-readable index that allows agents to discover relevant documentation without performing exhaustive file system searches. It serves as a "map" of the repository's knowledge, specifically curated for LLM-based agents.

## Schema Specification (v1.1.0)

### Top-Level Fields

| Field       | Type   | Required | Description                                                                  |
| ----------- | ------ | -------- | ---------------------------------------------------------------------------- |
| `version`   | String | Yes      | Schema version (e.g., "1.1.0").                                              |
| `docs`      | Array  | Yes      | List of documentation entries.                                               |
| `spec_dirs` | Array  | No       | Paths to directories containing authoritative specs (relative to repo root). |
| `includes`  | Array  | No       | Paths to other `context-map.json` files to include (e.g., for sub-projects). |

### Documentation Entry Fields (`docs[]`)

| Field         | Type   | Required | Description                                                                    |
| ------------- | ------ | -------- | ------------------------------------------------------------------------------ |
| `topic`       | String | Yes      | Unique snake_case identifier for the topic.                                    |
| `path`        | String | Yes      | Path to the file or directory relative to the repository root.                 |
| `description` | String | Yes      | One-sentence summary of what an agent will learn from this document.           |
| `keywords`    | Array  | Yes      | Search terms, synonyms, and natural language questions (e.g., "how do I...").  |
| `type`        | String | No       | Document category (axiom, heuristic, reference, spec, workflow, guide, index). |

## Design Decisions

### 1. Keys and Searchability

Entries are keyed by `topic` for programmatic reference, but discovered primarily via `keywords`. Keywords MUST include natural language queries an agent might use (e.g., "how do I run tests") to bridge the gap between intent and file paths.

### 2. Semantic Categories

The `type` field aligns with the framework's [[aops-core/TAXONOMY.md]]. This allows the hydrator to prioritise certain types of information (e.g., Axioms over Guides) when token budgets are tight.

### 3. Granularity and Scope

The map is **curated, not exhaustive**. It should contain 15-30 entries for a medium-sized repository. It focuses exclusively on documentation; agents are expected to find source code via `grep` and `glob` search tools.

### 4. Composability

The `includes` field supports monorepo structures by allowing a root map to reference sub-project maps. This prevents the root map from becoming bloated while maintaining a single entry point for discovery.

## Implementation Guidelines

1. **Lowercase Keywords**: All keywords should be lowercase for case-insensitive matching.
2. **Relative Paths**: All paths MUST be relative to the repository root.
3. **Existence**: Every `path` in the map MUST resolve to an existing file or directory.
4. **Maintenance**: The map should be updated whenever significant documentation is added, moved, or deleted (see [[aops-core/skills/project/workflows/context-map-audit.md]]).

## Example

```json
{
  "version": "1.1.0",
  "spec_dirs": ["specs/"],
  "docs": [
    {
      "topic": "taxonomy",
      "type": "reference",
      "path": "aops-core/TAXONOMY.md",
      "description": "Canonical definitions for all framework concepts",
      "keywords": ["taxonomy", "what is an epic", "task definition", "concepts"]
    }
  ]
}
```
