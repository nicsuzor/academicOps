---
title: Capture Workflow
type: workflow
permalink: capture-workflow
tags:
  - bmem
  - workflow
  - knowledge-management
---

# Capture Workflow

Session mining and note creation. Silently extracts information and maintains knowledge graph.

**Core principle**: If user says "can you save that?", you've already failed.

## What to Extract

### From Conversations

| Signal | Action |
|--------|--------|
| "I'll need to..." | Create task (invoke task skill) |
| Project updates | Update `data/projects/<project>.md` |
| Decisions made | Add observation to relevant file |
| Completed work | Invoke task skill to archive |
| Ruled-out ideas | Document why not |

### From Emails

1. Action items → task skill
2. Project mentions → update project files
3. Contacts/people → update project files
4. Deadlines → task skill
5. Strategic context → context files

## How to Capture

### Creating Notes

```python
mcp__bmem__write_note(
    title="Note Title",
    content="Full markdown content with frontmatter",
    folder="context",  # or projects, goals, etc.
    project="main"
)
```

### Editing Existing Notes

```python
mcp__bmem__edit_note(
    identifier="note-permalink",
    operation="append",  # or prepend, find_replace, replace_section
    content="New observation to add",
    project="main"
)
```

### Before Writing

1. **Search first**: Check for duplicates with `mcp__bmem__search_notes()`
2. **Use approved categories**: See [[approved-categories-relations]]
3. **Choose right location**: See file locations in [[bmem-skill-overview]]

### Append vs Create New

- **Recurring topics with sparse content** (meetings, working groups, periodic reviews): Append entries to a single topical note rather than creating per-instance notes
- **Only split by date** when the file becomes unwieldy
- **Create new note** when content is substantial enough to stand alone or represents a distinct topic

## Format Quick Reference

```markdown
---
title: Document Title
permalink: document-title
type: note
tags:
  - relevant-tag
---

# Document Title

## Context

1-3 sentences explaining what this is about.

## Observations

- [fact] Key fact about the topic #tag
- [decision] Choice made and why #tag

## Relations

- relates_to [[Other Note]]
- part_of [[Parent Project]]
```

## NEVER

- Interrupt user flow to ask clarification
- Wait until conversation end to capture
- Announce that you're capturing
- Create task files directly (use task skill)
