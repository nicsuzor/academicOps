---
name: remember
type: skill
category: instruction
description: Persist knowledge via PKB. PKB IS $ACA_DATA — never write to $ACA_DATA directly with Write/Edit.
triggers:
  - "remember this"
  - "save to memory"
  - "store knowledge"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: mcp__pkb__create,mcp__pkb__create_memory,mcp__pkb__append,mcp__pkb__get_document,mcp__pkb__search,mcp__pkb__update_task
owner: pauli
version: 3.0.0
---

# Remember Skill

> **Taxonomy note**: This skill provides domain expertise (HOW) for knowledge capture and persistence. See [[TAXONOMY.md]] for the skill/workflow distinction.

Persist knowledge via PKB. **PKB IS `$ACA_DATA`** — managed properly. The PKB MCP owns all writes, reads, indexing, deduplication, and linking. **Agents MUST NOT use `Write` or `Edit` on any path under `$ACA_DATA`** — that bypasses PKB's invariants and silently fails on environments where `$ACA_DATA` is a remote or differently-permissioned mount.

## Hard Rules

- ❌ `Write` or `Edit` on `$ACA_DATA/**` — forbidden.
- ❌ `Glob` / `Grep` on `$ACA_DATA/**` for semantic discovery — use `mcp__pkb__search`.
- ✅ `mcp__pkb__create` to create a document (projects, context, knowledge, meeting notes).
- ✅ `mcp__pkb__create_memory` to add a memory/note.
- ✅ `mcp__pkb__append` to extend an existing document.
- ✅ `mcp__pkb__get_document` to read.
- ✅ `mcp__pkb__search` to find existing content before creating.

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

**PKB is the single write interface for `$ACA_DATA`.** The markdown tree under `$ACA_DATA/` is PKB's internal representation, not a parallel target. A successful PKB call is the canonical persistence event; no filesystem follow-up is needed or allowed.

| What                  | Write Via                                       | Notes                                      |
| --------------------- | ----------------------------------------------- | ------------------------------------------ |
| **Epics/projects**    | `mcp__pkb__create` (`type="epic"/"project"`)    | Hub docs; PKB stores under `projects/`     |
| **Tasks/issues**      | `gh issue create` (GitHub is primary)           | PKB indexes via separate sync              |
| **Durable knowledge** | `mcp__pkb__create` or `mcp__pkb__create_memory` | PKB stores under `knowledge/`, `context/`… |
| **Session findings**  | `mcp__pkb__update_task` on the parent task      | Episodic → task body, not a new doc        |

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

- Individual agent actions: "Completed X on DATE" → `mcp__pkb__create_task(title="...", type="task", project="<project>", parent="<parent-id>")`
- Debugging logs: "Discovered bug in Y" → `mcp__pkb__create_task(title="...", type="task", project="<project>", parent="<parent-id>", tags=["bug"])`
- Experiment step-by-step records: "Tried approach A" → `mcp__pkb__update_task(id="...", body="...")`

**Rule**: If it describes agent activity or debugging, it's operational episodic → tasks MCP.

### Episodic Content in $ACA_DATA

- **Daily notes** (user-created summaries in `sessions/`) — `type: daily-note`
- **Meeting/call notes** (`type: meeting-note`) — contemporaneous records of conversations, captured close to the event
- **Contemporaneous observations** that may not be edited later — primary sources valued for their accuracy at the time of capture

## Canonical Topic Notes (Enduring Memory)

Semantic memory is organized around **canonical notes per first-class topic**. For every tool, project, skill, agent, or concept that matters, there is ONE note that holds the current understanding in stable sections. New insights route _into_ that note, updating the relevant section — they do not spawn parallel narrow notes.

**First-class topics** include tools (`mem`, `zotmcp`, `omcp`, the PKB MCP server), projects, skills (`/sleep`, `/planner`, `/remember`), agents (`pauli`), and named concepts ("task hierarchy", "enforcement pyramid", "sleep-cycle design"). If a thing has a name and will be worked on again, it is first-class.

**Stable sections** are the schema for a topic. Typical scaffolds:

- Tools: `Overview` / `Installation` / `Usage` / `Common Operations` / `Known Issues` / `Related`
- Projects: `Overview` / `Status` / `Decisions` / `Open Questions` / `Related`
- Concepts: `Definition` / `Implications` / `Examples` / `Open Questions`

Scaffolds are starting points — reshape as the material demands. The point is that agents know where to look and where to write.

### Routing Decision (before creating any new note)

1. _Is there a canonical note for this topic?_
   - **Yes** → update the relevant section via `mcp__pkb__append`, add to `sources:`, reconcile stale peers (see below).
   - **No, but the topic is first-class** → create the canonical note with a section scaffold via `mcp__pkb__create`, then populate the relevant section.
   - **No, and the observation is genuinely topic-less / one-off** → a narrow note is acceptable, but link it from the nearest canonical note so it's discoverable.

**Anti-pattern**: a separate file per observation (e.g. `kb-xxxx-tool-install-from-releases-not-source.md`). That content belongs _inside_ the tool's canonical note, under `Installation`. Narrow observation-files are episodic residue, not durable memory.

### Reconciliation (mandatory during updates)

Whenever you update a canonical topic note, search PKB for peer notes on the same topic and reconcile contradictions as part of the same write:

- Keep the stronger note (more sources, better synthesis, clearer thesis).
- Merge unique content from the weaker into the stronger.
- Retire the weaker: delete, or set `superseded_by:` pointing to the canonical.
- Update wikilinks that referenced the retired note.

Reconciliation is part of synthesis, not a separate cleanup chore. Never leave contradictory guidance in the PKB for a future agent to trip over. This applies to every write, not just `/sleep`-time consolidation.

### Canonical notes vs MOCs

A canonical topic note _is_ the knowledge; a Map of Content _indexes_ related canonical notes. Don't conflate them. You reach for a MOC when a topic area has 5+ canonical notes that need a navigational hub (see [Maps of Content (MOCs)](#maps-of-content-mocs) below).

## Workflow

1. **Search first**: `mcp__pkb__search(query="topic")`. Do not `Glob` or `Grep` `$ACA_DATA/` — PKB search is authoritative and respects indexing invariants.
2. **If match**: Extend the existing document via `mcp__pkb__append(id=..., content=...)`, or update task bodies via `mcp__pkb__update_task` for episodic additions. Do not fetch, edit locally, and rewrite.
3. **If no match**: Create via one of:

```
mcp__pkb__create(
  title="Descriptive Title",
  body="Content with [[wikilinks]] to related concepts.",
  type="note" | "project" | "epic" | "knowledge" | "moc" | "meeting-note",
  tags=["relevant", "tags"],
  # created / path / frontmatter fields handled by PKB
)
```

or, for lightweight atomic memories (observations, pointers, short facts):

```
mcp__pkb__create_memory(
  title="[descriptive title]",
  body="[content]",
  tags=["relevant", "tags"]
)
```

The body uses the frontmatter-less markdown shown in the format references below; PKB adds frontmatter (id, created, permalink) on write. **Never write the file yourself.**

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

Use `mcp__pkb__search` for all `$ACA_DATA/` content. **Never `grep`/`Glob`/`Read` markdown in the knowledge base** — you will see stale, unindexed, or partial state. PKB's semantic search respects the index and deduplication invariants that direct filesystem access bypasses. Give agents enough context to make decisions — never use algorithmic matching (fuzzy, keyword, regex).

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

Report the PKB write:

- Tool: `mcp__pkb__create` | `create_memory` | `append`
- Title: `[title]`
- ID / permalink: `[returned by PKB]`

Do **not** report a filesystem path — PKB owns the storage location. Referencing the filesystem path invites future agents to bypass PKB and edit it directly.
