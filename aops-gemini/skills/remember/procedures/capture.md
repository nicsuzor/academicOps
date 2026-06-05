---
title: Capture Workflow
type: automation
category: instruction
permalink: capture-workflow
tags:
  - memory
  - workflow
  - knowledge-management
---

# Capture Workflow

Session mining and note creation. Silently extracts information and maintains knowledge graph.

**Core principle**: If user says "can you save that?", you've already failed.

## What to Extract

### From Conversations

| Signal            | Action                              |
| ----------------- | ----------------------------------- |
| "I'll need to..." | Create task (invoke task skill)     |
| Project updates   | Update `data/projects/<project>.md` |
| Decisions made    | Add observation to relevant file    |
| Completed work    | Invoke task skill to archive        |
| Ruled-out ideas   | Document why not                    |

### From Emails

1. Action items → task skill
2. Project mentions → update project files
3. Contacts/people → update project files
4. Deadlines → task skill
5. Strategic context → context files

## How to Capture

### Creating Notes

Use `activate_skill(name="remember")`. Writes go via PKB MCP only — never the filesystem `write_file`/`replace` tool, and never directly to `$ACA_DATA/**`. PKB IS `$ACA_DATA`; direct filesystem access bypasses indexing, dedup, and permission guarantees.

1. Compose the content (body + title + tags).
2. Call `mcp_pkb_create_memory` (atomic memories) or `mcp_pkb_create` (full documents).

### Where to File (MANDATORY SEQUENCE)

1. **Search first**: `mcp_pkb_search(query="topic keywords")`
2. **Canonical Check Gate**: Check if a canonical note exists for this topic. If it does, you MUST augment the existing canonical document using `mcp_pkb_append`. Do NOT create a new observation-memo if a broader canonical note covers the topic area.
3. **If match found**: AUGMENT the existing document via `mcp_pkb_append(id=...)` — integrate info, don't append dated entries.
4. **If no match**: Create a new TOPICAL document (not session/date file) via `mcp_pkb_create`.

### Augment vs Concatenate

- ✅ **Augment**: Integrate new observations into existing structure
- ❌ **Concatenate**: Add "### 2025-12-17 Session" sections

Files organized by **topic**, not **date**. A project file should read as current state, not a changelog.

### Scale Guide

| Work Size            | Action                                          |
| -------------------- | ----------------------------------------------- |
| Tiny (one decision)  | Add bullet to existing project/context file     |
| Small (few outcomes) | Add observations to existing topical file       |
| Large (new topic)    | Create new topical file ONLY if nothing matches |

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

Content with [[wikilinks]] to related concepts.

## Relations

- relates_to [[Other Note]]
- part_of [[Parent Project]]
```

## NEVER

- Interrupt user flow to ask clarification
- Wait until conversation end to capture
- Announce that you're capturing
- Create task files directly (use task skill)
- Create timestamped session log files (use daily notes or meeting-note type instead)
- Append date-headers to existing files
- Skip the search step
