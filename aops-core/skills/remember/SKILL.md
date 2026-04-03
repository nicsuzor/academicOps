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

## Memory Model

`$ACA_DATA` contains both semantic and episodic memory. The key distinction is between _synthesized knowledge_ (decontextualized, kept current) and _primary sources_ (time-stamped, preserved as-is).

### Semantic Memory (synthesized knowledge)

Durable, decontextualized truths. Lives in `$ACA_DATA/knowledge/`, project files, context files.

- What IS true now. Understandable without history.
- If you must read multiple files or piece together history to understand truth, it's not properly synthesized.
- Always cites its episodic sources (see Provenance below).

### Episodic Memory (three types, all legitimate in $ACA_DATA)

1. **Task bodies** (`type: task`): Document what was done. Preserved even when archived. Managed via tasks MCP.
2. **Daily notes** (`type: daily-note`, in `sessions/`): High-quality user synthesis of what happened and what matters. Created by the user. NOT edited after the day.
3. **Contemporaneous notes** (`type: meeting-note`, in `knowledge/` or project dirs): Notes of meetings, phone calls, conversations. Captured close to the event. May not be edited afterwards. Valuable as primary sources.

### Cognitive Foundations

The episodic/semantic distinction mirrors how biological memory works. Complementary Learning Systems theory (McClelland et al. 1995) shows that rapid episode capture and gradual pattern extraction are complementary processes — you need both. Semanticization (Baddeley 1988) is the natural process where episodic memories lose temporal context through repeated retrieval, becoming context-free semantic knowledge. The /sleep cycle's consolidation phases mirror this: offline replay of episodes, pattern extraction, integration into durable knowledge. The review process IS the consolidation mechanism — passive storage does not produce understanding.

### Synthesis Flow (the consolidation pipeline)

- Episodic content accumulates → patterns emerge across multiple notes
- Agent or human extracts observations → creates/updates semantic knowledge notes
- Semantic notes always cite their episodic sources (provenance)
- The transformation from episodic to semantic mirrors cognitive semanticization
- Git history preserves the full record; semantic notes in `$ACA_DATA` reflect what's current

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
Is this a time-stamped observation? (what agent did, found, tried)
  → YES: Use tasks MCP (create_task or update_task) - NOT this skill
  → NO: Continue...

Is this about the framework (axioms, heuristics)?
  → YES: HALT and invoke /framework skill to add properly to $AOPS
  → NO: Continue...

Is this about the user? (projects, goals, context, tasks)
  → YES: Use appropriate location below
  → NO: Use `knowledge/<topic>/` for general facts
```

## File Locations

| Content                | Location                            | Notes                                       |
| ---------------------- | ----------------------------------- | ------------------------------------------- |
| Project metadata       | `projects/<name>.md`                | Hub file                                    |
| Project details        | `projects/<name>/`                  | Subdirectory                                |
| Goals                  | `goals/`                            | Strategic objectives                        |
| Context (about user)   | `context/`                          | Preferences, history                        |
| Sessions/daily         | `sessions/`                         | Daily notes only, `type: daily-note`        |
| Tasks                  | Delegate to [[tasks]]               | Use scripts                                 |
| **General knowledge**  | `knowledge/<topic>/`                | Facts NOT about user                        |
| Meeting/call notes     | `knowledge/<topic>/` or `projects/` | Contemporaneous notes, `type: meeting-note` |
| Maps of Content (MOCs) | `knowledge/` or topic dirs          | Navigational hub notes, `type: moc`         |

## Episodic Content → Where It Belongs

### Use Tasks MCP (NOT $ACA_DATA files)

- Individual agent actions: "Completed X on DATE" → `mcp__pkb__create_task(task_title="...", type="task", project="<project>", parent="<parent-id>")`
- Debugging logs: "Discovered bug in Y" → `mcp__pkb__create_task(task_title="...", type="task", project="<project>", parent="<parent-id>", tags=["bug"])`
- Experiment step-by-step records: "Tried approach A" → `mcp__pkb__update_task(id="...", body="...")`

**Rule**: If it describes agent activity or debugging, it's operational episodic → tasks MCP.

### Episodic Content in $ACA_DATA

- **Daily notes** (user-created summaries in `sessions/`) — `type: daily-note`
- **Meeting/call notes** (`type: meeting-note`) — contemporaneous records of conversations, captured close to the event
- **Contemporaneous observations** that may not be edited later — primary sources valued for their accuracy at the time of capture

## Workflow

1. **Search first**: `mcp__pkb__search(query="topic")` + `Glob` under `$ACA_DATA/`
2. **If match**: Augment existing file
3. **If no match**: Create new file with frontmatter:

```markdown
---
title: Descriptive Title
type: note|project|knowledge|moc|meeting-note|daily-note
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

## Observation Notation

When extracting facts or observations from episodic content, use Obsidian callout syntax:

> [!observation] Brief factual claim
> Source: [[link-to-source-note]] or description of origin
> Confidence: established | provisional | speculative

**Examples:**

> [!observation] Platform liability frameworks increasingly distinguish between hosting and curation
> Source: [[20260401-meeting-regulators]], discussion with policy team
> Confidence: established

<!-- -->

> [!observation] Sleep cycle deduplication catches ~15% false positives on short titles
> Source: Three /sleep runs in March 2026
> Confidence: provisional

**Guidelines:**

- One fact per observation block
- Always include source — never assert facts without provenance
- Confidence levels: `established` (multiple independent sources), `provisional` (single source or limited evidence), `speculative` (inference, needs verification)
- Observations in episodic notes (daily, meeting) are raw material; observations in knowledge notes are synthesized claims
- Humans may also write observations informally as plain prose — the callout format is a recommendation, not a requirement
- **Contradictions**: When a new observation contradicts an existing one, record BOTH with their sources. Never silently overwrite. Flag for human resolution. This prevents catastrophic forgetting — schema-inconsistent information must be integrated gradually, not by replacement.

## Provenance

All synthesized knowledge must be traceable to its sources. This is critical — we never fabricate information.

### Frontmatter Fields

For synthesized knowledge notes, include:

```yaml
sources:
  - "[[daily/20260401-daily]]"
  - "[[meeting-notes/regulatory-review-20260328]]"
  - "Session transcript 2026-04-01T14:30"
synthesized: 2026-04-03
confidence: provisional
maturity: seedling
last_reviewed: 2026-04-03
```

**Maturity levels** (optional, tracks evidence strength):

- `seedling` — single source, provisional confidence. May not survive review.
- `budding` — corroborated by 2+ independent sources. Worth linking to.
- `evergreen` — reviewed, stable, established confidence. Core knowledge.

### Inline Attribution

When a specific claim comes from a specific source, cite it inline:

- "Platform liability is shifting toward curation-based models ([[20260401-meeting-regulators]])"
- Use `[[wikilinks]]` for $ACA_DATA sources, markdown links for external sources

### Rules

- **Never synthesize without attribution** — if you can't cite where a claim came from, don't assert it
- **Distinguish observation from editorial** — agents extract and synthesize but leave editorializing to the user
- **Preserve uncertainty** — use confidence levels. Don't upgrade `provisional` to `established` without additional evidence
- **Source chain**: When synthesizing from other synthesized notes, include the full chain (the intermediate synthesis AND its original sources)

## Maps of Content (MOCs)

A Map of Content is a navigational hub note that curates links to related notes on a topic.

### When to Create

Create a MOC when a topic area reaches a "mental squeeze point" — typically 5+ related notes that would benefit from a navigational index. MOCs are created by the /sleep consolidation cycle or manually.

### Format

```yaml
---
title: "MOC: Topic Name"
type: moc
tags: [moc, topic-area]
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
---
```

### Structure

MOCs contain curated links with brief annotations, grouped thematically:

```markdown
# MOC: Platform Regulation

## Core Concepts

- [[platform-liability-frameworks]] — distinction between hosting and curation models
- [[content-moderation-at-scale]] — practical challenges of automated enforcement

## Australian Context

- [[osb-act-overview]] — Online Safety Bill structure and key provisions
- [[esafety-commissioner-powers]] — regulatory enforcement mechanisms

## Open Questions

- How will AI-generated content affect platform liability? (no settled answer yet)
```

### Maintenance

- MOCs should be reviewed when the /sleep cycle detects they may be stale
- Add new notes to relevant MOCs when creating them
- Split MOCs that grow beyond ~30 entries

## General Knowledge (Fast Path)

For factual observations NOT about the user. Location: `knowledge/<topic>/`

**Constraints:**

- Aim for concise notes (under 500 words for knowledge, under 200 for atomic facts)
- [[wikilinks]] on ALL proper nouns
- One fact per file for atomic knowledge; synthesized notes may cover a topic

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
