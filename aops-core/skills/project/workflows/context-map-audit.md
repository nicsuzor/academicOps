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

Scan for reference docs, index files, specs, and design docs. Exclude source code, test files (unless they document patterns), generated files, and archives. Typical locations: `README.md`, `docs/`, `specs/`, `aops-core/`, `.agents/`.

### 2. Load and validate existing map

Read `.agents/context-map.json` (or start fresh). For each entry: does the file exist? Is the description accurate? Are keywords sufficient for an agent to find it?

### 3. Identify gaps

For each unmapped doc: "Would an agent benefit from discovering this via keyword search?" If yes, add it. Also check concept coverage — can agents find definitions for every term in the project's taxonomy, architectural decisions, conventions, and workflow documentation?

### 4. Write the updated map

```json
{
  "spec_dirs": ["specs/"],
  "docs": [
    {
      "topic": "short_snake_case_identifier",
      "path": "relative/path/from/repo/root.md",
      "description": "What will I learn by reading this?",
      "keywords": ["formal term", "natural language query an agent might use"]
    }
  ]
}
```

For a secondary repo whose specs live under `docs/specs/`, the same field would be:

```json
{
  "spec_dirs": ["docs/specs/"],
  "docs": [ ... ]
}
```

### 5. Report changes

Summarise entries added, removed, updated — in the commit message or response.

## Schema Rules

### Top-level fields

- **`spec_dirs`**: Array of directories containing authoritative specs; consumed by `/review-pr` and Pauli to surface spec divergence. Paths are relative to repo root and should end with `/` for clarity. Omit or leave empty (`[]`) if the repo has no dedicated spec directory — consumers degrade gracefully. Example: `"spec_dirs": ["specs/"]` for this repo; `"spec_dirs": ["docs/specs/"]` for a secondary repo whose specs live under `docs/`.
- **`docs`**: Array of documentation entries (see below).

### `docs[]` entry fields

- **`topic`**: Unique snake_case identifier, descriptive of content not filename.
- **`path`**: Relative to repo root. Must resolve to an existing file or directory.
- **`description`**: One sentence answering "what will I learn?" not "what is this file."
- **`keywords`**: 5-15 lowercase terms/phrases including both formal terms and natural language queries.

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
