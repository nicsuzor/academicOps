---
title: Validate Workflow
type: workflow
permalink: validate-workflow
tags:
  - bmem
  - workflow
  - maintenance
---

# Validate Workflow

Check format compliance and fix issues in `data/` files.

## When to Use

- "fix bmem", "validate files", "check compliance"
- After bulk imports or migrations
- Periodic maintenance

## What Gets Checked

### Format Compliance

| Check | Requirement |
|-------|-------------|
| Frontmatter | title, permalink, type required |
| Permalink | lowercase, hyphens only, no slashes |
| H1 heading | Must match title exactly |
| Observations | Use [[approved-categories-relations|approved categories]] only |
| Relations | Must have `[[wiki-links]]`, use [[approved-categories-relations|approved types]] |

### Location Compliance

| Location | Allowed Content |
|----------|----------------|
| `data/context/` | General notes, background |
| `data/goals/` | Objectives and targets |
| `data/projects/` | Project metadata |
| `data/<project>/` | Project-specific files |
| `data/tasks/inbox/` | Active tasks |

### Prohibited

- Root-level working documents
- Files without clear category
- Duplicate content
- Session detritus

## Scripts

```bash
# Validate all files
PYTHONPATH=$AOPS uv run python $AOPS/skills/bmem/scripts/bmem_tools.py validate

# Fix common issues (dry-run first)
PYTHONPATH=$AOPS uv run python $AOPS/skills/bmem/scripts/bmem_fix.py --dry-run

# Apply fixes
PYTHONPATH=$AOPS uv run python $AOPS/skills/bmem/scripts/bmem_fix.py

# Find broken links
PYTHONPATH=$AOPS uv run python $AOPS/skills/bmem/scripts/validate_links.py --suggest

# Ensure folder indexes exist
PYTHONPATH=$AOPS uv run python $AOPS/skills/bmem/scripts/ensure_indexes.py

# Find potential duplicates
PYTHONPATH=$AOPS uv run python $AOPS/skills/bmem/scripts/find_duplicates.py

# Analyze tag usage
PYTHONPATH=$AOPS uv run python $AOPS/skills/bmem/scripts/analyze_tags.py
```

## Common Fixes

### Invalid Permalink

```yaml
# Bad
permalink: my/path/here
permalink: My Title

# Good
permalink: my-path-here
permalink: my-title
```

### Relation Syntax

```markdown
# Bad
- **Label**: [[Link]]
- Label: [[Link]]
- relates-to [[Link]]

# Good
- relates_to [[Link]]
- part_of [[Parent]]
```

### H1 Mismatch

```markdown
---
title: My Document Title
---

# My Document Title  ← Must match exactly
```

## Workflow

1. **Scan**: List files in target directory
2. **Check**: Run validation on each file
3. **Report**: Categorize issues (auto-fixable vs manual)
4. **Fix**: Apply automatic fixes
5. **Review**: Present manual fixes needed
