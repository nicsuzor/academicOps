---
title: Obsidian File Format Specification
type: reference
category: ref
permalink: obsidian-format-spec
tags:
  - memory
  - reference
  - obsidian
  - format
---

# Obsidian File Format Specification

Obsidian uses standard Markdown with YAML frontmatter. Files are plain `.md` text files.

## YAML Frontmatter

Must be at the very top of the file, delimited by triple dashes:

```yaml
---
title: Note Title
tags: [tag1, tag2, tag3]
aliases: [Alternative Name]
permalink: note-title
type: note
---
```

**Requirements:**
- Position: Absolute top of file (no content before opening `---`)
- Syntax: Valid YAML with `key: value` pairs (space after colon)

**Multiple values** - either format works:
```yaml
tags: [tag1, tag2]        # inline
tags:                     # multiline
  - tag1
  - tag2
```

## Tags

**We use frontmatter tags only** (not inline `#tags`) to keep prose clean and copyable.

**Allowed characters**: letters, numbers, `_`, `-`, `/` (for nesting)
**Restrictions**: No spaces, colons, periods. Cannot start with numbers.
**Case**: Tags are case-insensitive (`#Research` = `#research`)

## Wiki Links

```markdown
[[Related Note]]                    # Basic link
[[Note Title|Display Text]]         # Custom display
[[folder/subfolder/Note]]           # Path to file
[[Note#Heading]]                    # Link to heading
```

## Standard Format

```markdown
---
title: Document Title
permalink: document-title
type: note
tags:
  - relevant-tag
---

# Document Title

Content here.

## Relations

- relates_to [[Other Note]]
- part_of [[Parent Project]]
```

**H1 must match title exactly.**

## Markdown Support

Standard CommonMark plus:
- Task lists: `- [ ]` and `- [x]`
- Tables, footnotes, highlighting (`==text==`)
- Callouts: `> [!note]`
- Math: `$inline$` and `$$block$$`

## Best Practices

1. Keep frontmatter minimal: title, permalink, type, tags
2. Use lowercase tags with hyphens
3. 3-5 tags usually sufficient
4. Link liberally (forward references are fine)
