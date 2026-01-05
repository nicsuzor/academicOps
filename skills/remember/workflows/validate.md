---
title: Validate Workflow
type: automation
permalink: validate-workflow
tags:
  - memory
  - workflow
  - maintenance
---

# Validate Workflow

Check format compliance and fix issues in `data/` files.

## When to Use

- "validate files", "check compliance"
- After bulk imports or migrations
- Periodic maintenance

## What Gets Checked

### Format Compliance

| Check | Requirement |
|-------|-------------|
| Frontmatter | title, permalink, type required |
| Permalink | lowercase, hyphens only, no slashes |
| H1 heading | Must match title exactly |
| Relations | Must have `[[wiki-links]]` |

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
