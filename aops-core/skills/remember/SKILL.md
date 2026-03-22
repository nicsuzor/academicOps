---
name: remember
type: skill
category: instruction
description: Write knowledge to markdown AND sync to PKB. MUST invoke - do not write markdown directly.
triggers:
  - "remember this"
  - "save to memory"
  - "store knowledge"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Read,Write,Edit,mcp__pkb__create_memory,mcp__pkb__search
version: 2.0.0
---

# Remember Skill

> **Taxonomy note**: This skill provides domain expertise (HOW) for knowledge capture and persistence. See [[TAXONOMY.md]] for the skill/workflow distinction.

Persist knowledge to markdown + PKB. **Both writes required** for semantic search.

## What $ACA_DATA Is

`$ACA_DATA` is the **personal knowledge corpus** — all persistent, personal knowledge artifacts deliberately kept. It contains three tiers:

- **Episodic records**: Time-stamped content kept verbatim for reference (diary, meeting notes, observations, reading notes). Lives in `meetings/`, `journal/`, `reviews/`, `<project>/observations/`.
- **Synthesized knowledge**: Timeless, atomic, maintained notes. Lives in `knowledge/`, `context/`, `projects/`, `goals/`.
- **Navigation/index**: MEMORY.md, project hubs, Maps of Content.

What does NOT live in `$ACA_DATA`:

- Active work items and agent activity logs → tasks MCP
- Unreviewed raw session transcripts → `sessions/transcripts/` (excluded from indexing)

**Synthesis flow**: Episodic records accumulate → patterns emerge → synthesize to knowledge docs (HEURISTICS, specs) → link back to source records. Synthesis is a bonus, not a requirement — episodic records have permanent retrieval value on their own.

## Storage Hierarchy (Critical)

**PKB is the universal index.** Write to your primary storage AND PKB for semantic search retrieval.

| What                  | Primary Storage                         | Also Sync To |
| --------------------- | --------------------------------------- | ------------ |
| **Epics/projects**    | PKB (`type="epic"` or `type="project"`) | PKB index    |
| **Tasks/issues**      | GitHub Issues (`gh issue create`)       | PKB index    |
| **Durable knowledge** | `$ACA_DATA/` markdown files             | PKB index    |
| **Session findings**  | Task body updates                       | PKB index    |

See [[base-memory-capture]] workflow for when and how to invoke this skill.

## Decision Tree

```
Is this agent activity from a work session?
  (what the agent did, found, tried, decided during a task)
  → YES: Update task body via tasks MCP. NOT this skill.

Is this a work item to be done?
  (has status, lifecycle, dependencies)
  → YES: Create/update task via tasks MCP. NOT this skill.

Is this observational tracking of a pattern (not actionable)?
  → YES: Create learn-type task via tasks MCP. NOT this skill.

Is this a meeting note, diary entry, or field observation?
  (time-stamped, human-authored, kept verbatim)
  → YES: Write to $ACA_DATA as episodic record (see File Locations).

Is this a reading note or literature annotation?
  (extracted ideas from a source)
  → YES: $ACA_DATA/reviews/<slug>.md, type: review

Is this about the framework (axioms, heuristics, conventions)?
  → YES: HALT and invoke /framework skill to add properly to $AOPS

Is this a synthesized, timeless fact or concept?
  → YES: $ACA_DATA/knowledge/<topic>/<slug>.md, type: knowledge, max 200 words

Is this about the user (projects, goals, context)?
  → YES: Use appropriate location below (projects/, goals/, context/)
```

## File Locations

| Content              | Location                                     | Type        | Notes                                              |
| -------------------- | -------------------------------------------- | ----------- | -------------------------------------------------- |
| Meeting notes        | `meetings/YYYY-MM-DD-topic.md`               | `note`      | `date:` frontmatter required; one file per meeting |
| Diary/journal        | `journal/YYYY-MM-DD.md`                      | `note`      | `date:` frontmatter required                       |
| Project observations | `<project>/observations/YYYY-MM-DD-topic.md` | `note`      | `date:` frontmatter required                       |
| Reading/review notes | `reviews/<slug>.md`                          | `review`    | Source, extracted ideas                            |
| Daily notes          | `sessions/YYYY-MM-DD.md`                     | `daily`     | `sync: false` unless content promoted              |
| Project metadata     | `projects/<name>.md`                         | `project`   | Hub file; "standup level" only                     |
| Project details      | `projects/<name>/`                           | —           | Subdirectory for specs, detailed notes             |
| Goals                | `goals/`                                     | `goal`      | Strategic objectives                               |
| Context (about user) | `context/`                                   | `note`      | Preferences, history, biographical                 |
| General knowledge    | `knowledge/<topic>/`                         | `knowledge` | Synthesized facts; max 200 words                   |
| Tasks                | Delegate to [[tasks]]                        | —           | Use tasks MCP, not this skill                      |

## Tasks MCP — for agent activity and work items only

Use tasks MCP (NOT this skill) for:

- What an agent did: "Completed X on DATE" → `mcp__pkb__create_task(task_title="...", type="task", project="<project>", parent="<parent-id>")`
- What an agent found: "Discovered bug in Y" → `mcp__pkb__create_task(task_title="...", type="task", project="<project>", parent="<parent-id>", tags=["bug"])`
- Observational tracking: "Noticed pattern Z" → `mcp__pkb__create_task(task_title="Learning: Z", type="learn", project="<project>", parent="<parent-id>")`
- Experiments: "Tried approach A" → `mcp__pkb__update_task(id="...", body="...")`
- Decisions during work: "Chose B over C" → update task body, synthesize to HEURISTICS.md later

**Rule**: Tasks MCP is for work items (things with actionable status, lifecycle, and graph hierarchy) and agent activity logs. It is NOT the home for human-authored meeting notes, diary entries, or field observations — those go to `$ACA_DATA` as episodic records.

## Workflow

1. **Search first**: `mcp__pkb__search(query="topic")` + `Glob` under `$ACA_DATA/`
2. **If match**: Augment existing file (for semantic notes). For episodic records, create a new dated file — never append a new entry to an existing episodic file.
3. **If no match**: Create new file with appropriate frontmatter:

**Episodic record** (meeting, diary, observation):

```markdown
---
title: "Meeting: Topic (YYYY-MM-DD)"
type: note
date: YYYY-MM-DD
tags: [meeting, project-name]
---

# Meeting: Topic (YYYY-MM-DD)

Content.
```

**Synthesized knowledge**:

```markdown
---
title: Descriptive Title
type: knowledge
tags: [relevant, tags]
created: YYYY-MM-DD
---

Content with [[wikilinks]] to related concepts.
```

4. **Sync to PKB**:

```
mcp__pkb__create_memory(
  title="[descriptive title]",
  body="[content]",
  tags=["relevant", "tags"]
)
```

## Graph Integration

- Every file MUST [[wikilink]] to at least one related concept
- Project files link to [[goals]] they serve
- Knowledge files link proper nouns: [[Google]], [[Eugene Volokh]]
- **Semantic Link Density**: Files about same topic/project/event MUST link to each other in prose. Project hubs link to key content files.

### External References (REQUIRED)

When a memory references an external issue, bug, or resource, **always link it explicitly**:

- **Upstream bugs**: `[org/repo#NNN](https://github.com/org/repo/issues/NNN)` — don't just mention "#NNN" in prose
- **Internal issues**: `gh issue create` link or `[#NNN](url)`
- **Related PKB nodes**: Add a `## Relationships` section with typed edges:
  ```
  ## Relationships
  - [related] [[task-id]] — brief description
  - [upstream-bug] [org/repo#NNN](url)
  - [parent] [[parent-id]]
  ```

**Why**: Unlinked references are dead ends. The PKB graph and future agents can't traverse prose mentions — they need explicit edges.

## Wikilink Conventions

- **Wikilinks in Prose Only**: Only add [[wikilinks]] in prose text. Never inside code fences, inline code, or table cells with technical content.
- **Semantic Wikilinks Only**: Use [[wikilinks]] only for semantic references in prose. NO "See Also" or cross-reference sections.

## Semantic Search

Use PKB semantic search for `$ACA_DATA/` content. Never grep for markdown in the knowledge base. Give agents enough context to make decisions - never use algorithmic matching (fuzzy, keyword, regex).

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
