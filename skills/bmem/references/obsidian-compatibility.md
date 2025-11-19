# Obsidian Compatibility

## Tags

**CRITICAL: All tags go in YAML frontmatter, NEVER inline in observations.**

```yaml
tags:
  - academic-writing
  - research-methods
  - platform-governance
  - security-metrics
```

**In observations - NO hashtags**:

```markdown
- [insight] 2FA adoption increased security by 40%
- [pattern] Multi-factor authentication reduces unauthorized access
```

**Tag format requirements**:
- Use hyphens for multi-word tags (Obsidian-compatible)
- Allowed characters: Letters, numbers, hyphens, underscores, forward slash
- NOT allowed: Spaces, periods, starting with numbers

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
