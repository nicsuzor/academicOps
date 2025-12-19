---
name: reference-map
description: Extract all file references from framework and output standard graph format for visualization. Pure state capture.
allowed-tools: Bash,Read
version: 1.0.0
permalink: skills-reference-map
---

# Reference Map Skill

Extract ALL file references from the framework and output a standard node-link JSON graph.

## Quick Start

```bash
PYTHONPATH=$AOPS uv run python $AOPS/skills/reference-map/scripts/build_reference_map.py
```

Output: `$AOPS/reference-graph.json`

## What It Captures

| Type | Pattern | Example |
|------|---------|---------|
| `wikilink` | `[[target]]` | `[[AXIOMS.md]]` |
| `wikilink_aliased` | `[[target\|display]]` | `[[README\|overview]]` |
| `markdown_link` | `[text](path)` | `[guide](./file.md)` |
| `python_import` | `from X import Y` | `from lib.paths import get_aops_root` |
| `env_path` | `$VAR/path` | `$AOPS/hooks/file.py` |
| `at_inclusion` | `@path/to/file` | `@docs/HOOKS.md` |
| `path_literal` | Quoted paths | `"./file.md"` |

## Output Format

Standard node-link JSON (D3, NetworkX, Gephi compatible):

```json
{
  "generated": "2025-12-19T10:30:00Z",
  "framework_root": "/path/to/academicOps",
  "nodes": [{"id": "CLAUDE.md"}, {"id": "lib/paths.py"}],
  "links": [
    {
      "source": "CLAUDE.md",
      "target": "skills/framework/SKILL.md",
      "weight": 3,
      "ref_type": "wikilink",
      "path_category": "relative",
      "refs": [{"line": 10, "raw": "[[skills/framework/SKILL.md]]"}]
    }
  ]
}
```

## Path Categories

Each edge includes `path_category`:

- `env_var` - `$AOPS/...`, `${ACA_DATA}/...`
- `absolute` - `/Users/.../file.py`
- `relative` - `./file.md`, `../dir/file.md`, `file.md`
- `module` - `lib.paths`, `skills.tasks.models`

## Use Cases

1. **Visualize framework structure** - Load JSON into D3.js, Gephi, or Obsidian
2. **Find orphan files** - Nodes with no incoming edges
3. **Find broken references** - Targets that don't exist in nodes
4. **Analyze coupling** - Which files are most connected
5. **Verify documentation** - Are all skills/hooks referenced from docs?

## Options

```bash
# Custom output path
PYTHONPATH=$AOPS uv run python $AOPS/skills/reference-map/scripts/build_reference_map.py --output /path/to/graph.json

# Custom root (default: $AOPS)
PYTHONPATH=$AOPS uv run python $AOPS/skills/reference-map/scripts/build_reference_map.py --root /path/to/repo
```
