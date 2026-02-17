---
name: remember
category: instruction
description: Write knowledge to markdown AND sync to memory server. MUST invoke - do not write markdown directly.
allowed-tools: Read,Write,Edit,mcp__memory__store_memory
version: 2.0.0
---

# Remember Skill

Persist knowledge to markdown + memory server. **Both writes required** for semantic search.

## Current State Machine

`$ACA_DATA` contains ONLY semantic memory - timeless truths, always up-to-date:

- **Semantic memory** (current state): What IS true now. Understandable without history. Lives in `$ACA_DATA`.
- **Episodic memory** (observations): Time-stamped events. Lives in **tasks** (`data/tasks/`, managed via tasks MCP).
- **Episodic content includes**: Bug investigations, experiment observations, development logs, code change discussions, decision rationales, any observation at a point in time
- **Synthesis flow**: Observations accumulate in tasks → patterns emerge → synthesize to semantic docs (HEURISTICS, specs) → complete task with link to synthesized content
- If you must read multiple files or piece together history to understand truth, it's not properly synthesized
- Git history preserves the record; `$ACA_DATA` reflects only what's current

## Storage Hierarchy (Critical)

**Memory MCP is the universal index.** Write to your primary storage AND memory MCP for semantic search retrieval.

| What                  | Primary Storage                                      | Also Sync To |
| --------------------- | ---------------------------------------------------- | ------------ |
| **Epics/projects**    | Task Manager MCP (`type="epic"` or `type="project"`) | Memory MCP   |
| **Tasks/issues**      | GitHub Issues (`gh issue create`)                    | Memory MCP   |
| **Durable knowledge** | `$ACA_DATA/` markdown files                          | Memory MCP   |
| **Session findings**  | Task body updates                                    | Memory MCP   |

See [[base-memory-capture]] workflow for when and how to invoke this skill.

## Decision Tree

```
Is this a time-stamped observation? (what agent did, found, tried)
  → YES: Use tasks MCP (create_task or update_task) - NOT this skill
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

## PROHIBITED → Use Tasks MCP Instead

**NEVER create files for:**

- What an agent did: "Completed X on DATE" → `mcp__plugin_aops-core_task_manager__create_task(task_title="...", type="task")`
- What an agent found: "Discovered bug in Y" → `mcp__plugin_aops-core_task_manager__create_task(task_title="...", type="task", tags=["bug"])`
- Observations: "Noticed pattern Z" → `mcp__plugin_aops-core_task_manager__create_task(task_title="Learning: Z")`
- Experiments: "Tried approach A" → `mcp__plugin_aops-core_task_manager__update_task(id="...", body="...")`
- Decisions: "Chose B over C" → update task body, synthesize to HEURISTICS.md later

**Rule**: If it has a timestamp or describes agent activity, it's episodic → tasks MCP.

## Workflow

1. **Search first**: `mcp__memory__retrieve_memory(query="topic")` + `Glob` under `$ACA_DATA/`
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
- **Semantic Link Density**: Files about same topic/project/event MUST link to each other in prose. Project hubs link to key content files.

## Wikilink Conventions

- **Wikilinks in Prose Only**: Only add [[wikilinks]] in prose text. Never inside code fences, inline code, or table cells with technical content.
- **Semantic Wikilinks Only**: Use [[wikilinks]] only for semantic references in prose. NO "See Also" or cross-reference sections.

## Semantic Search

Use memory server semantic search for `$ACA_DATA/` content. Never grep for markdown in the knowledge base. Give agents enough context to make decisions - never use algorithmic matching (fuzzy, keyword, regex).

## Abstraction Level (CRITICAL for Framework Work)

When capturing learnings from debugging/development sessions, **prefer generalizable patterns over implementation specifics**.

| ❌ Too Specific                                                       | ✅ Generalizable                                                   |
| --------------------------------------------------------------------- | ------------------------------------------------------------------ |
| "AOPS_SESSION_STATE_DIR env var set at SessionStart in router.py:350" | "Configuration should be set once at initialization, no fallbacks" |
| "Fixed bug in session_paths.py on 2026-01-28"                         | "Single source of truth prevents cascading ambiguity"              |
| "Gemini uses ~/.gemini/tmp/<hash>/ for state"                         | "Derive paths from authoritative input, don't hardcode locations"  |

**Why this matters**: Specific implementation details are only useful for one code path. Generalizable patterns apply across all future framework work. We're dogfooding - capture what helps NEXT session, not what happened THIS session.

**Test**: Would this memory help an agent working on a DIFFERENT component? If not, it's too specific.

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
