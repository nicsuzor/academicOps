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

### Where to File (MANDATORY SEQUENCE)

1. **Search first**: `mcp__bmem__search_notes(query="topic keywords", project="main")`
2. **If match found**: AUGMENT existing file (integrate info, don't append dated entry)
3. **If no match**: Create new TOPICAL file (not session/date file)
4. **Use approved categories**: See [[approved-categories-relations]]

### Augment vs Concatenate

- ✅ **Augment**: Integrate new observations into existing structure
- ❌ **Concatenate**: Add "### 2025-12-17 Session" sections

Files organized by **topic**, not **date**. A project file should read as current state, not a changelog.

### Scale Guide

| Work Size | Action |
|-----------|--------|
| Tiny (one decision) | Add bullet to existing project/context file |
| Small (few outcomes) | Add observations to existing topical file |
| Large (new topic) | Create new topical file ONLY if nothing matches |

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
- Create timestamped session files (except transcripts)
- Append date-headers to existing files
- Skip the search step
