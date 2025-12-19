---
name: link-audit
description: Analyze and clean up framework file references using reference-map output. Enforce linking conventions.
allowed-tools: Bash,Read,Edit
version: 1.0.0
permalink: skills-link-audit
---

# Link Audit Skill

Analyze framework file references to identify and fix violations of linking conventions. Uses `Skill(skill="reference-map")` output for systematic graph analysis.

## When to Use

- Periodic framework hygiene
- After bulk file additions/moves
- When investigating tangled dependencies
- Before major refactors

## Linking Rules

### R1: Skills via Invocation, Not File Reference

When directing an agent to use a skill, use Claude's invocation syntax, NOT a file path.

| Anti-pattern | Correct |
|--------------|---------|
| `[[skills/framework/SKILL.md]]` | `Skill(skill="framework")` |
| `[[../bmem/SKILL.md]]` | `Skill(skill="bmem")` |

**Rationale**: Skills are invoked at runtime via the Skill tool, not read as files.

### R2: Hierarchical Structure - No Backward Links

Links flow downward. Child files (templates, references, examples) do NOT link back up to their parent.

| Anti-pattern | Correct |
|--------------|---------|
| `templates/foo.md` → `../SKILL.md` | Remove the link |
| `README.md` → `./SKILL.md` | Remove the link |

**Rationale**: Parent→child is discovery. Child→parent is circular noise.

### R3: Parent Must Reference Children

Reference docs, workflows, templates, and scripts inside a skill directory should be linked from the parent SKILL.md. Otherwise they're invisible to the graph.

| Anti-pattern | Correct |
|--------------|---------|
| `skills/x/references/foo.md` exists but not linked | Add `[[references/foo.md]]` to SKILL.md |
| `skills/x/workflows/` directory unreferenced | Add workflows section to SKILL.md |

**Rationale**: Orphaned children are effectively dead code.

### R4: Use Wikilinks, Not Backticks

For graph connectivity, use wikilink syntax, not code backticks.

| Anti-pattern | Correct |
|--------------|---------|
| `- \`templates/foo.md\`` | `- [[templates/foo.md]]` |
| `See \`references/bar.md\`` | `See [[references/bar.md]]` |

**Rationale**: Backticks are display-only. Wikilinks create graph edges.

### R5: Full Relative Paths in Wikilinks

Include the subdirectory in wikilink paths.

| Anti-pattern | Correct |
|--------------|---------|
| `[[foo.md]]` (in SKILL.md) | `[[references/foo.md]]` |

**Rationale**: Bare names may not resolve; explicit paths always work.

### R6: Directory Index Files Match Directory Name

Index/overview files should be named after their parent directory, not `README.md`.

| Anti-pattern | Correct |
|--------------|---------|
| `skills/tasks/README.md` | `skills/tasks/tasks.md` |
| `skills/extractor/README.md` | `skills/extractor/extractor.md` |

**Rationale**: Reduces ambiguity when multiple README.md files exist. Directory name is more descriptive.

## Workflow

### 1. Generate Reference Graph

```bash
PYTHONPATH=$AOPS uv run python $AOPS/skills/reference-map/scripts/build_reference_map.py
```

Outputs: `$AOPS/reference-graph.json`, `$AOPS/reference-graph.csv`

### 2. Find Orphans and Disconnected Clusters

```bash
PYTHONPATH=$AOPS uv run python $AOPS/skills/link-audit/scripts/find_orphans.py
```

Reports:
- **Unexpected orphans** - files never referenced (but not entry points/tests)
- **Completely isolated** - files with no refs in or out (potentially dead)
- **Disconnected clusters** - groups linked to each other but not to main framework

**Expected orphans** (filtered out): commands/, agents/, hooks/*.py, tests/, scripts/*.py, __init__.py, entry points.

### 3. Find SKILL.md Links (R1 Violations)

```python
import json
with open('reference-graph.json') as f:
    g = json.load(f)

skill_links = [l for l in g['links'] if 'SKILL.md' in l['target']]
for link in sorted(skill_links, key=lambda x: x['source']):
    print(f"{link['source']} -> {link['target']} (line {link['refs'][0]['line']})")
```

### 4. Find Backward Links (R2 Violations)

Look for patterns:
- `templates/*.md` → `../SKILL.md`
- `references/*.md` → `../SKILL.md`
- `README.md` → `SKILL.md` (same directory)
- `workflows/*.md` → `../SKILL.md`

### 5. Categorize and Triage

| Category | Action |
|----------|--------|
| Agent instructions ("use the X skill") | Convert to `Skill(skill="x")` |
| "Related" sections with cross-skill refs | Convert to `Skill(skill="x")` |
| Backward links from children | Remove entirely |
| Meta-documentation (examples, tables) | Keep - legitimate |
| Different runtime context (e.g., Gemini) | Defer - document for later |
| Orphaned reference docs | Link from parent SKILL.md or delete |
| Isolated files | Evaluate: link, move, or delete |

### 6. Fix and Verify

After edits, re-run reference-map and find_orphans until violations are resolved.

### 7. Document

Update `$ACA_DATA/projects/aops/links.md` with:
- Rules established
- Observations from audit
- Deferred items
- Cleanup summary

## Common Fix Patterns

| Problem | Fix |
|---------|-----|
| Duplicate `*.md` alongside SKILL.md (e.g., `analyst.md` + `SKILL.md`) | Delete the duplicate |
| References listed with backticks | Convert to wikilinks |
| `[[foo.md]]` not resolving | Add subdirectory: `[[references/foo.md]]` |
| Orphaned workflows/references/templates | Add section in parent SKILL.md linking them |
| Cross-skill refs like `[[../bmem/SKILL.md]]` | Convert to `Skill(skill="bmem")` |
| Backward links in "Related" sections | Remove the parent link |
| `README.md` in subdirectory | Rename to match directory: `tasks/README.md` → `tasks/tasks.md` |

## Expected Orphans

Some files legitimately have no incoming wikilinks:

- **SKILL.md files** - Referenced via `Skill(skill="x")` format (R1 compliant)
- **Entry points** - CLAUDE.md, README.md loaded by Claude Code directly
- **Scripts** - Invoked via Bash, not wikilinked
- **hooks/*.py** - Loaded by hook system
- **tests/** - Standalone test files

## Example Session

```
# Generate graph
PYTHONPATH=$AOPS uv run python $AOPS/skills/reference-map/scripts/build_reference_map.py
# Found 268 nodes, 328 edges

# Find orphans
PYTHONPATH=$AOPS uv run python $AOPS/skills/link-audit/scripts/find_orphans.py
# 32 unexpected orphans, 15 isolated, 89 components

# Fix issues:
# - Delete 4 duplicate *.md files
# - Add workflows section to framework/SKILL.md (6 links)
# - Add references section to framework/SKILL.md (9 links)
# - Fix python-dev reference paths (10 links)
# - Convert backticks to wikilinks in feature-dev

# Re-run and verify
# 271 nodes, 364 edges
# 14 unexpected orphans, 6 isolated, 78 components
# Main component: 176 -> 192 nodes
```

## Related

- `Skill(skill="reference-map")` - Generates the graph
- `$ACA_DATA/projects/aops/links.md` - Linking rules and audit history
