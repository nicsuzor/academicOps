---
title: Reference-Map Skill
type: spec
status: implemented
permalink: reference-map-skill
tags:
  - skill
  - framework
  - visualization
  - reference-map
---

# Reference-Map Skill

**Status**: Implemented

## Workflow

```mermaid
graph LR
    A[Scan $AOPS Files] --> B[Extract References]
    B --> C[WikiLinks]
    B --> D[Python Imports]
    B --> E[Env Paths]
    B --> F[@Inclusions]
    C --> G[Build Graph]
    D --> G
    E --> G
    F --> G
    G --> H[reference-graph.json]
```

## Summary

New skill that extracts ALL file references from the [[aops]] framework and outputs standard node-link JSON for visualization.

## What It Does

- Scans all `.md`, `.py`, `.json`, `.sh` files in `$AOPS`
- Extracts 7 reference types: wikilinks, aliased wikilinks, markdown links, Python imports, env paths, @inclusions, path literals
- Outputs `reference-graph.json` in standard format (D3, NetworkX, Gephi compatible)
- Pure state capture - no analysis or computed metrics

## Key Design Decisions

1. **Capture everything, filter later**: External tools filter what they need. Script captures all references.
2. **Standard format**: Node-link JSON compatible with common visualization tools
3. **Path categories as metadata**: Each edge tagged with `env_var`, `absolute`, `relative`, or `module`
4. **Output to repo root**: `$AOPS/reference-graph.json` (gitignored)

## Audit Results (2025-12-19)

| Pattern | Occurrences | Files |
|---------|-------------|-------|
| Wikilinks | 610 | 101 |
| Env vars | 406 | 70 |
| Python imports | 52 | 39 |
| @inclusions | 7 | 7 |

## Usage

```bash
PYTHONPATH=$AOPS uv run python $AOPS/skills/reference-map/scripts/build_reference_map.py
```

Output: 990 nodes, 2346 edges

