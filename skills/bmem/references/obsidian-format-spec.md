# Obsidian File Format Specification

## Overview

Obsidian uses standard Markdown with YAML frontmatter for metadata. Files are plain `.md` text files with optional structured metadata at the top.

## YAML Frontmatter

### Basic Structure

YAML frontmatter must be at the very top of the file, delimited by triple dashes:

```yaml
---
title: Note Title
tags: [tag1, tag2, tag3]
aliases: [Alternative Name, Another Alias]
---
```

### Format Requirements

1. **Position**: Must be at the absolute top of the file (no content before opening `---`)
2. **Delimiters**: Triple dashes (`---`) on separate lines
3. **Syntax**: Valid YAML format with `key: value` pairs
4. **Spacing**: Requires `key: value` format with space after colon

### Native Obsidian Fields

Obsidian natively supports only a few fields:

- `tags` or `tag`: Tags for the note
- `aliases` or `alias`: Alternative names for the note
- `cssclass` or `cssclasses`: Custom CSS classes for styling
- `publish`: Publishing status (for Obsidian Publish)
- `permalink`: URL slug (for Obsidian Publish)

### Custom Fields

You can add any custom YAML fields for your own use:

```yaml
---
title: My Note
date: 2025-01-15
status: in-progress
priority: high
author: John Doe
---
```

Custom fields are available for:

- Dataview queries
- Templater scripts
- Custom plugins
- Your own organization system

### Multiple Value Formats

For fields with multiple values, use either array or list format:

**Array format (inline)**:

```yaml
tags: [tag1, tag2, tag3]
aliases: [name1, name2]
```

**List format (multiline)**:

```yaml
tags:
  - tag1
  - tag2
  - tag3
aliases:
  - name1
  - name2
```

Both formats are equivalent. Choose based on preference and readability.

## Tags

### Inline Tags

Tags can appear anywhere in the document body using `#tag` syntax:

```markdown
This is a note about #research and #academic-writing.
```

### Tag Format Requirements

**Allowed characters**:

- Alphabetical letters (A-Z, a-z)
- Numbers (0-9)
- Underscore (`_`)
- Hyphen (`-`)
- Forward slash (`/`) for nested tags
- Unicode characters (non-English languages, emoji, symbols)

**Restrictions**:

- No spaces (use hyphens or underscores instead)
- Numbers must be combined with non-numerical characters (#a2023, not #2023)
- Cannot start with numbers
- No colons (`:`)
- No periods (`.`)
- No other special punctuation (ampersands, etc.)

**Case sensitivity**:

- Tags are case-insensitive
- `#Research` and `#research` are treated as the same tag

### Nested Tags

Use forward slashes for hierarchical tags:

```markdown
#research/methods/qualitative #projects/academic/publications
```

### Frontmatter vs Inline Tags

Both methods work and are indexed identically:

**Frontmatter**:

```yaml
---
tags: [research, academic, writing]
---
```

**Inline**:

```markdown
#research #academic #writing
```

**Combined approach**:

```yaml
---
tags: [research, academic]
---

This note is about #writing and #editing.
```

All four tags (#research, #academic, #writing, #editing) will be indexed.

## Links

### Wiki Links

Obsidian uses `[[WikiLinks]]` for internal linking:

```markdown
See [[Related Note]] for more information. [[Note Title|Display Text]] for custom display. [[folder/subfolder/Note]] for specific paths.
```

**Link features**:

- Auto-complete suggestions as you type
- Backlinks automatically tracked
- Links work even if target doesn't exist yet (forward references)
- Can link to specific headings: `[[Note#Heading]]`
- Can link to blocks: `[[Note#^block-id]]`

### Aliases

Define alternative names in frontmatter:

```yaml
---
aliases: [Alt Name, Another Name]
---
```

Now `[[Alt Name]]` will link to this note.

## Markdown Compatibility

Obsidian supports standard CommonMark Markdown plus extensions:

### Standard Markdown

- Headings: `# H1` through `###### H6`
- **Bold**: `**text**` or `__text__`
- _Italic_: `*text*` or `_text_`
- Lists: `- item` or `1. item`
- Code: `` `inline` `` or `` ```block``` ``
- Blockquotes: `> quote`
- Links: `[text](url)`
- Images: `![alt](url)`

### Obsidian Extensions

- Task lists: `- [ ] task` and `- [x] done`
- Footnotes: `[^1]` with definition `[^1]: text`
- Tables: Standard Markdown tables
- Highlighting: `==highlighted==`
- Comments: `%%hidden comment%%`
- Callouts: `> [!note]` and other types
- Mermaid diagrams: ``mermaid`
- Math: `$inline$` and `$$block$$`

## File Organization

### File Naming

- Use any valid filename
- `.md` extension required
- Spaces are allowed in filenames
- Special characters may cause issues on some systems

### Folder Structure

- Organize files in any folder hierarchy
- No special meaning to folders (unlike some systems)
- Links work across folders
- Can use relative or absolute paths in links

## Best Practices

### Frontmatter

1. Keep frontmatter at the top
2. Use consistent field names across notes
3. Use arrays for multi-value fields
4. Add custom fields as needed for queries

### Tags

1. Use lowercase for consistency (system is case-insensitive)
2. Use hyphens or underscores for multi-word tags
3. Create hierarchies with nested tags
4. Don't over-tag (3-5 tags usually sufficient)

### Links

1. Use descriptive note titles for better linking
2. Add aliases for common alternative names
3. Link liberally (forward references are fine)
4. Use heading links for specific sections

## Integration with Other Tools

### Compatibility

- Plain Markdown files work in any Markdown editor
- YAML frontmatter is standard (Jekyll, Hugo, etc.)
- `[[WikiLinks]]` are Obsidian-specific but easy to convert
- Git-friendly (plain text, good diffs)

### Export

- Files are portable Markdown
- Can convert WikiLinks to standard Markdown links
- YAML frontmatter is preserved or easily stripped
- Works with static site generators

## Version Notes

This specification is based on Obsidian v1.x (2024-2025). Tag character support may have changed from earlier versions based on user reports and GitHub issues.

## References

- Obsidian Help: https://help.obsidian.md
- Obsidian Forum: https://forum.obsidian.md
- GitHub Issues: https://github.com/obsidianmd/obsidian-help
