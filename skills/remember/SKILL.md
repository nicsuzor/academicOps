---
name: remember
category: instruction
description: Write knowledge to markdown AND sync to memory server. MUST invoke - do not write markdown directly.
allowed-tools: Read,Write,Edit,mcp__memory__store_memory
version: 2.0.0
---

# Remember Skill

Persist knowledge to markdown + memory server. **Both writes required** for semantic search.

## Decision Tree

```
Is this a time-stamped observation? (what agent did, found, tried)
  → YES: Use `bd create` or `bd update` - NOT this skill
  → NO: Continue...

Is this about the user? (projects, goals, context, tasks)
  → YES: Use appropriate location below
  → NO: Use `knowledge/<topic>/` for general facts
```

## File Locations

| Content               | Location              | Notes                |
| --------------------- | --------------------- | -------------------- |
| Project metadata      | `projects/<name>.md`  | Hub file             |
| Project details       | `projects/<name>/`    | Subdirectory         |
| Goals                 | `goals/`              | Strategic objectives |
| Context (about user)  | `context/`            | Preferences, history |
| Sessions/daily        | `sessions/`           | Daily notes only     |
| Tasks                 | Delegate to [[tasks]] | Use scripts          |
| **General knowledge** | `knowledge/<topic>/`  | Facts NOT about user |

## PROHIBITED → Use `bd` Instead

**NEVER create files for:**

- What an agent did: "Completed X on DATE" → `bd create --type=task`
- What an agent found: "Discovered bug in Y" → `bd create --type=bug`
- Observations: "Noticed pattern Z" → `bd create --type=task --title="Learning: Z"`
- Experiments: "Tried approach A" → bd issue comment
- Decisions: "Chose B over C" → bd issue comment, synthesize to HEURISTICS.md later

**Rule**: If it has a timestamp or describes agent activity, it's episodic → bd.

## Workflow

1. **Search first**: `mcp__memory__retrieve_memory(query="topic")` + `Glob`
2. **If match**: Augment existing file
3. **If no match**: Create new file with frontmatter:

```markdown
---
title: Descriptive Title
type: note|project|knowledge
tags: [relevant, tags]
created: YYYY-MM-DD
---

Content with [[wikilinks]] to related concepts.
```

4. **Sync to memory server**:

```
mcp__memory__store_memory(
  content="[content]",
  metadata={"source": "[path]", "type": "[type]"}
)
```

## Graph Integration

- Every file MUST [[wikilink]] to at least one related concept
- Project files link to [[goals]] they serve
- Knowledge files link proper nouns: [[Google]], [[Eugene Volokh]]

## General Knowledge (Fast Path)

For factual observations NOT about the user. Location: `knowledge/<topic>/`

**Constraints:**

- Max 200 words - enables dense vector embeddings
- [[wikilinks]] on ALL proper nouns
- One fact per file

**Topics** (use broadly):

- `cyberlaw/` - copyright, defamation, privacy, AI ethics, platform law
- `tech/` - protocols, standards, technical facts
- `research/` - methodology, statistics, findings

**Format:**

```markdown
---
title: Fact/Case Name
type: knowledge
topic: cyberlaw
source: Where learned
date: YYYY-MM-DD
---

[[Entity]] did X. Key point: Y. [[Person]] observes: "quote".
```

## Background Capture

For non-blocking capture, spawn background agent:

```
Task(
  subagent_type="general-purpose", model="haiku",
  run_in_background=true,
  description="Remember: [summary]",
  prompt="Invoke Skill(skill='remember') to persist: [content]"
)
```

## Output

Report both operations:

- File: `[path]`
- Memory: `[hash]`
