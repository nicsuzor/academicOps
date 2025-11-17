# Obsidian Compatibility

## Tags

**Use hyphens in tags** (Obsidian-compatible):

```yaml
tags:
  - academic-writing
  - research-methods
  - platform-governance
```

**Inline tags**:

```markdown
- [insight] 2FA adoption increased security by 40% #security-metrics
```

**Allowed characters**: Letters, numbers, hyphens, underscores, forward slash **NOT allowed**: Spaces, periods, starting with numbers

## WikiLinks

Use `[[Entity Title]]` syntax for all entity references:

```markdown
See [[Platform Governance Research]] for background.

## Relations

- part_of [[Research Program]]
- supports [[World-Class Academic Profile]]
```

**Aliases** (in frontmatter):

```yaml
aliases:
  - Short Name
  - Alternative Name
```
