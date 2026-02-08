---
title: personal knowledge base
type: instructions
---

# About this system

This is a [[Zettelkasten]]-style personal knowledge base. Notes are atomic, densely linked, and written in plain markdown with YAML frontmatter. The system is designed to be human-first but navigable by AI agents.

## Core principles

1. **Atomic notes**: One idea per note. If you're tempted to add a heading, make a new note instead.
2. **Concept-oriented**: Notes are about ideas, not sources. "Confirmation bias" not "Kahneman 2011 notes."
3. **Reformulation over capture**: Never copy. Rewrite in your own words. The work is the thinking.
4. **Dense linking**: Every note should link to at least one other note. Orphans are failures.
5. **Extended cognition**: This system is part of thinking, not a record of it.

## Frontmatter schema

Every note uses this structure:

```yaml
---
type: note
created: 2024-12-22
updated: 2024-12-22
aliases: [alternate name, abbreviation]
permalink: 202412221430
tags: [optional, for-filtering]
---
```

### Required fields

| Field       | Purpose                                                      |
| ----------- | ------------------------------------------------------------ |
| `type`      | What kind of note this is (see Note types below)             |
| `created`   | When the note was created (YYYY-MM-DD)                       |
| `permalink` | Stable identifier, usually the timestamp portion of filename |

### Optional fields

| Field     | Purpose                                             |
| --------- | --------------------------------------------------- |
| `updated` | Last modified date                                  |
| `aliases` | Alternate names for wikilink resolution             |
| `tags`    | Additional categorisation, use sparingly            |
| `status`  | For notes in progress: `draft`, `active`, `archive` |
| `source`  | For source notes: bibliographic reference           |

## Note types

Keep this set small. If you need a new type, you probably need a tag instead.

### concept

An atomic idea. The core unit of the system. Reusable, linkable, could be referenced from anywhere.

Example: `202412221430 extended cognition.md`

### moc

Map of Content. An index note that links to related concepts. Not a folder—a note that creates structure through links. Every concept should eventually be reachable from a MOC.

Example: `personal knowledge management.md`

### decision

A choice made, with reasoning. Inspired by Architecture Decision Records. Captures _why_ so future-you understands past-you.

Structure:

- What was decided
- Context at the time
- Reasoning
- Consequences accepted

Example: `202412221445 decision — plain markdown pkm.md`

### pattern

Something reliably true about the note-taker, their context, or their tendencies. Self-knowledge that influences decisions.

Example: `202412221500 my tendency to system-hop.md`

### source

A book, paper, article, or other reference. Contains bibliographic info and key ideas extracted (in your own words). Links to concept notes, not the other way around—concepts shouldn't depend on sources.

Example: `202412221515 source — bush 1945 as we may think.md`

### log

Timestamped, context-heavy capture. Daily notes, conversation summaries, event records. Less refined than concepts. The raw material from which concepts may later be extracted.

Example: `2024-12-22 log.md`

## Filename conventions

```
[timestamp] [type prefix if useful] — [title].md
```

- Timestamps: `YYYYMMDDHHMM` or `YYYY-MM-DD` for logs
- The timestamp is the permalink—stable even if the title changes
- Lowercase, hyphens for spaces in timestamp portion
- Title in natural case

Examples:

- `202412221430 extended cognition.md`
- `202412221445 decision — plain markdown pkm.md`
- `2024-12-22 log.md`
- `personal knowledge management.md` (MOCs can skip timestamp)

## Linking conventions

### Wikilinks

Use `[[note title]]` or `[[note title|display text]]`. Obsidian resolves these.

```markdown
See: [[extended cognition]]
This relates to [[202412221430|Clark's extended mind thesis]].
```

### Link placement

Links appear in two places:

1. **Inline**: When referencing an idea in prose
2. **Footer**: Under `See:` or `Related:` for explicit connections

```markdown
# Some concept

Content discussing [[other concept]] inline.

More content.

See: [[related concept]], [[another one]]
```

### Link density

Every note should have at least one outgoing link. Notes with zero links or zero backlinks need attention. The graph should be one connected component.

### MOC linking

MOCs link _to_ concepts. Concepts link _to each other_. This creates navigable clusters.

## For AI agents

### Orientation

Start with this note. Then read any MOC note to understand the current topic clusters.

### Finding relevant notes

1. Check MOCs for topic areas
2. Follow wikilinks from known-relevant notes
3. Use `type:` frontmatter to filter (e.g., all decisions, all patterns)
4. Backlinks reveal what references a given note

### Understanding the user

- `pattern` notes describe the user's tendencies and self-knowledge
- `decision` notes reveal past choices and reasoning
- Recent `log` notes provide current context

### Adding new notes

When creating notes on behalf of the user:

1. Make it atomic—one idea only
2. Choose the correct type
3. Include frontmatter with type, created, permalink
4. Write in prose, in the user's voice
5. Add at least one wikilink to an existing note
6. Consider which MOC it belongs under and add a link

### Conventions to maintain

- Never copy text verbatim; always reformulate
- Prefer links to tags
- Keep frontmatter minimal—if a field isn't used, omit it
- When in doubt, make a new atomic note rather than adding to an existing one

## Graph navigation

The visual graph is a primary navigation tool. Structure emerges from links, not folders.

- **Clusters**: Form around MOCs
- **Bridges**: Concepts that connect clusters are high-value
- **Orphans**: Notes with no links need integration or deletion
- **Hubs**: Notes with many backlinks are core ideas
