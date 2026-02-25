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

<!-- NS: this should be merged into 'remember' skill -->
<!-- @claude 2026-01-12: Issue ns-3p3 created to track merging this workflow into the remember skill -->

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

### From External Artifacts (Diagrams, Old Documents, Maps)

When importing from an external source (Excalidraw, old project maps, planning docs, etc.), the primary value is **connections between existing nodes**, not new nodes.

**Import sequence:**

1. Identify all entities mentioned in the artifact
2. Search for each: `mcp__memory__retrieve_memory(query="entity")`
3. For entities that already exist, **check their connections** — do relationships to the *other* entities in this artifact already exist in the graph?
4. **Missing connections are the import target.** Augment existing nodes with links to each other, cross-project relationships, and strategic context from the artifact.
5. Only create new nodes for genuinely uncaptured concepts.

**What to extract:**

| Signal                       | Action                                             |
| ---------------------------- | -------------------------------------------------- |
| Two known projects linked    | Add [[wikilinks]] between their existing nodes     |
| Strategic tension identified | Capture as observation on relevant project/goal    |
| Cross-project dependency     | Add relationship links to both project files       |
| Deployment philosophy        | Add to context or project strategy files           |
| New concept                  | Create new topical file (last resort)              |

**Key principle:** "Already captured" means the node exists AND its relationships to other mentioned entities are in the graph. A node without its connections is incomplete.

## How to Capture

### Creating Notes

Use `Skill(skill="remember")` which handles both file creation and memory server sync:

1. Write markdown file with proper frontmatter
2. Sync to memory server via `mcp__memory__store_memory`

### Where to File (MANDATORY SEQUENCE)

1. **Search first**: `mcp__memory__retrieve_memory(query="topic keywords")`
2. **If match found**: AUGMENT existing file (integrate info, don't append dated entry)
3. **If no match**: Create new TOPICAL file (not session/date file)

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
