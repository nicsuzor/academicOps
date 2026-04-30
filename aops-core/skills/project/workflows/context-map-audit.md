---
id: context-map-audit
name: context-map-audit
category: maintenance
bases: []
description: Create or update .agents/context-map.json — the repo's self-description for agent discovery
permalink: workflows/context-map-audit
tags: [workflow, context-map, discovery, maintenance, index]
version: 1.0.0
---

# Context Map Audit

**Purpose**: Ensure `.agents/context-map.json` exists, is accurate, and covers all documentation an agent working in this repo would need to discover. The context map is a plain JSON file — any agent on any platform can read it. Not indexed by PKB; consumed directly via file read.

**Owner**: `/project` skill. **Invoke**: on scaffolding, manually ("audit the context map"), or when significant docs are added/moved/deleted.

## Core Process

### 1. Inventory documentation files

Scan for reference docs, index files, specs, and design docs. Exclude source code, test files (unless they document patterns), generated files, and archives. Typical locations: `README.md`, `docs/`, `aops-core/`, `.agents/`. (Some downstream projects also keep specs in `specs/` or `docs/specs/`; the aops framework itself stores specs in the brain PKB.)

### 2. Load and validate existing map

Read `.agents/context-map.json` (or start fresh). For each entry: does the file exist? Is the description accurate? Are keywords sufficient for an agent to find it?

### 3. Identify gaps

For each unmapped doc: "Would an agent benefit from discovering this via keyword search?" If yes, add it. Also check concept coverage — can agents find definitions for every term in the project's taxonomy, architectural decisions, conventions, and workflow documentation?

### 4. Write the updated map

```json
{
  "version": "1.1.0",
  "spec_dirs": [],
  "includes": [".agents/subproject/context-map.json"],
  "docs": [
    {
      "topic": "short_snake_case_identifier",
      "type": "spec",
      "path": "relative/path/from/repo/root.md",
      "description": "What will I learn by reading this?",
      "keywords": ["formal term", "natural language query an agent might use"]
    }
  ]
}
```

`spec_dirs` is empty for the aops framework (specs live in the brain PKB).
For a secondary repo whose specs live in-tree under `docs/specs/`, use:

```json
{
  "spec_dirs": ["docs/specs/"],
  "docs": [ ... ]
}
```

### 5. Report changes

Summarise entries added, removed, updated — in the commit message or response. Use `mcp__pkb__append` to record mid-workflow if a task is in progress.

## Schema

Full field definitions and design rationale live in the brain PKB (project: aops, topic: context-map-schema) — SSoT. Key fields: `version`, `spec_dirs`, `includes`, `docs[]` (each entry has `topic`, `type`, `path`, `description`, `keywords`).

### Audit checklist

When auditing, verify each of these fields:

- [ ] `spec_dirs` — present if the repo has an authoritative specs directory; each entry resolves to an existing directory; consumers (`/review-pr`, Pauli) will find specs there.
- [ ] `docs` — curated, not exhaustive; each entry's `path` exists; descriptions are accurate; keywords cover both formal terms and natural-language queries.

## Anti-Patterns

- **Indexing everything**: Curated, not exhaustive. 15-30 entries for a medium repo.
- **Stale descriptions**: Worse than no entry. Re-read the file when in doubt.
- **Code files**: Agents find code via grep/glob. Map documentation only.
- **Duplicating content**: The map points TO docs, never contains explanations itself.

## Maintenance Triggers

1. **Scaffolding**: `/project` creates the initial map for new repos.
2. **Manual**: User or agent requests an audit.
3. **Advisory**: Agents creating new docs should check whether the map needs an entry.
