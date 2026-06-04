---
name: remember
type: skill
category: instruction
description: "Unified memory skill: immediate mode (/remember) persists knowledge via PKB MCP; maintenance mode (/sleep, GHA cron) runs periodic consolidation — transcript mining, knowledge synthesis, data quality, brain sync."
triggers:
  - "remember this"
  - "save to memory"
  - "store knowledge"
  - "sleep cycle"
  - "consolidation"
  - "brain maintenance"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: mcp__pkb__create,mcp__pkb__create_memory,mcp__pkb__append,mcp__pkb__get_document,mcp__pkb__search,mcp__pkb__update_task,Bash,Read,Write,Grep,Glob,Edit,Skill,mcp__pkb__pkb_orphans,mcp__pkb__list_tasks,mcp__pkb__graph_stats,mcp__pkb__get_network_metrics,mcp__pkb__get_task,mcp__pkb__task_search,mcp__pkb__pkb_context,mcp__pkb__bulk_reparent,mcp__pkb__find_duplicates,mcp__pkb__batch_merge,mcp__pkb__merge_node,mcp__pkb__complete_task,mcp__pkb__batch_reclassify,mcp__pkb__batch_archive,mcp__pkb__batch_update,mcp__pkb__create_task,mcp__pkb__update_memory,mcp__omcp__messages_search,mcp__omcp__messages_query,mcp__omcp__calendar_list_events
owner: pauli
version: 4.0.0
---

# Memory Skill

> **Modes**: **Immediate** (`/remember`) — write a memory/task/doc now via PKB MCP. **Maintenance** (`/sleep`, GHA cron) — periodic consolidation: transcript mining, knowledge synthesis, data quality, graph maintenance. Immediate mode requires PKB MCP. Maintenance mode works directly on markdown files in CI contexts (no PKB MCP). Full maintenance phase instructions: [[references/maintenance-phases]].
>
> **Taxonomy note**: This skill provides domain expertise (HOW) for knowledge capture and persistence. See [[references/TAXONOMY.md]] for the skill/workflow distinction.

## Immediate Mode

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

**Consolidation Ownership**: Tend to the PKB while your context is fresh. When you encounter something worth remembering — a decision, a resolved question, a pattern — create or update a knowledge note now. The offline `/sleep` maintenance cycle provides comprehensive, systematic consolidation of raw session logs, episodic records, and task history on a regular schedule; it is a complement to inline curation, not a replacement for it. Your responsibility in immediate mode is:

1. **Capture** episodic records accurately in the moment.
2. **Curate** — when you encounter something worth consolidating into durable knowledge, do it while context is fresh. Agents must not defer all synthesis to `/sleep`.
3. **Retrieve**: You MUST search the PKB (`mcp__pkb__search`) before asserting facts or creating new knowledge notes. Don't assume; look it up.

### Semantic Memory (synthesized knowledge)

Durable, decontextualized truths. Lives in `$ACA_DATA/knowledge/`, project files, context files.

- What IS true now. Understandable without history.
- If you must read multiple files or piece together history to understand truth, it's not properly synthesized.
- Always cites its episodic sources (see Provenance below).

### Episodic Memory (three types, all legitimate in $ACA_DATA)

1. **Task bodies** (`type: task`): Document what was done. Preserved even when archived. Managed via tasks MCP.
2. **Daily notes** (`type: daily-note`, in `sessions/`): High-quality user synthesis of what happened and what matters. Created by the user. NOT edited after the day.
3. **Contemporaneous notes** (`type: meeting-note`, in `knowledge/` or project dirs): Notes of meetings, phone calls, conversations. Captured close to the event. May not be edited afterwards. Valuable as primary sources.

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

| Content                | Location                            | Notes                                                                                            |
| ---------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------ |
| Project metadata       | `projects/<name>.md`                | Hub file. The location is a storage directory, not a type assertion; the hub-doc type is `epic`. |
| Project details        | `projects/<name>/`                  | Subdirectory                                                                                     |
| Goals                  | `goals/`                            | Strategic objectives                                                                             |
| Context (about user)   | `context/`                          | Preferences, history                                                                             |
| Sessions/daily         | `sessions/`                         | Daily notes only, `type: daily-note`                                                             |
| Tasks                  | Delegate to [[tasks]]               | Use scripts                                                                                      |
| **General knowledge**  | `knowledge/<topic>/`                | Facts NOT about user                                                                             |
| Meeting/call notes     | `knowledge/<topic>/` or `projects/` | Contemporaneous notes, `type: meeting-note`                                                      |
| Maps of Content (MOCs) | `knowledge/` or topic dirs          | Navigational hub notes, `type: moc`                                                              |

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
2. **Canonical Check Gate**: Before creating a new standalone memory, explicitly check if a canonical note already exists for this topic. If it does, you MUST append to the canonical note using `mcp__pkb__append` or update the relevant section. Do NOT create narrow observation-memos if a broader canonical note covers the topic area.
3. **If match**: Extend the existing document via `mcp__pkb__append(id=..., content=...)`, or update task bodies via `mcp__pkb__update_task` for episodic additions. Do not fetch, edit locally, and rewrite.
4. **If no match**: Create via one of:

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

### Multi-Parent & Strategic Linkage

Strategic cross-cutting linkage to terminal obligations uses `contributes_to` edges (see [[multi-parent]]) — not extra `parent` edges, not a separate `goals: []` field. Knowledge synthesis written during `/sleep` should follow the same model when linking work to targets.

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
- **`confidence`** (numeric 0.0–1.0): the PKB schema value used by search ranking. Higher values rank above lower in retrieval. Human-readable status descriptors that map onto numeric ranges:
  - `established` (≥ 0.8): multiple independent sources, reviewed
  - `provisional` (0.4–0.79): single source or limited evidence
  - `speculative` (< 0.4): inference, needs verification

  Use the numeric value in frontmatter; describe the level in prose if helpful.
- Observations in episodic notes (daily, meeting) are raw material; observations in knowledge notes are synthesized claims
- Humans may also write observations informally as plain prose — the callout format is a recommendation, not a requirement
- **Contradictions**: When a new observation contradicts an existing one, record BOTH with their sources. Never silently overwrite. Flag for human resolution. This prevents catastrophic forgetting — schema-inconsistent information must be integrated gradually, not by replacement.

## Provenance

All synthesized knowledge must be traceable to its sources. This is critical — we never fabricate information.

### Frontmatter Fields

For `type: knowledge` notes, the following frontmatter fields are REQUIRED:

- `synthesized:` (ISO date) — when this synthesis was performed
- `last_reviewed:` (ISO date) — most recent review/refresh
- `sources:` (list of strings) — must be a YAML list, even with one element. Episodic notes and primary sources cited here.
- `confidence:` (numeric 0.0–1.0)

Memory and episodic notes (daily, meeting, etc.) do NOT require these — they're observations, not synthesis.

Example:

```yaml
sources:
  - "[[daily/20260401-daily]]"
  - "[[meeting-notes/regulatory-review-20260328]]"
  - "Session transcript 2026-04-01T14:30"
synthesized: 2026-04-03
confidence: 0.6
maturity: seedling
last_reviewed: 2026-04-03
```

**Maturity levels** (optional, tracks evidence strength — independent of the numeric `confidence` value):

- `seedling` — single source, low confidence (typically `provisional` range, ~0.4–0.6). May not survive review.
- `budding` — corroborated by 2+ independent sources. Worth linking to.
- `evergreen` — reviewed, stable, high confidence (typically `established` range, ≥ 0.8). Core knowledge.

### Inline Attribution

When a specific claim comes from a specific source, cite it inline:

- "Platform liability is shifting toward curation-based models ([[20260401-meeting-regulators]])"
- Use `[[wikilinks]]` for $ACA_DATA sources, markdown links for external sources

### Rules

- **Never synthesize without attribution** — if you can't cite where a claim came from, don't assert it
- **Distinguish observation from editorial** — agents extract and synthesize but leave editorializing to the user
- **Preserve uncertainty** — use the numeric `confidence` value (0.0–1.0). Don't upgrade a note from the `provisional` range (0.4–0.79) into the `established` range (≥ 0.8) without additional evidence
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

## Maintenance Mode

**Trigger**: `/sleep` command or `sleep-cycle` GitHub Actions workflow.
**Purpose**: Periodic offline consolidation — transforming write-optimised storage (tasks, session logs) into durable semantic knowledge that agents can retrieve.

This mirrors biological memory consolidation (Complementary Learning Systems, McClelland et al. 1995): episodic memories are replayed offline to extract durable semantic patterns. The review IS the consolidation — passive storage does not produce understanding.

### Values

1. **Never fabricate** — only extract what is grounded in source material. If you can't cite it, don't assert it.
2. **Always track provenance** — every synthesized fact must cite its source. The chain from claim → source must be traversable.
3. **Preserve episodic originals** — never modify daily notes, meeting notes, or task bodies. Only add `consolidated: YYYY-MM-DD` to their frontmatter.
4. **Leave editorializing to the user** — agents extract patterns and connections; value judgments are the user's domain.
5. **Respect uncertainty** — use confidence levels honestly. Don't upgrade `provisional` to `established` without additional independent evidence.
6. **Quality over quantity** — one well-sourced synthesis note beats ten unsourced assertions.
7. **Knowledge writing standards defer to Immediate Mode** — canonical topic notes, reconciliation, maturity, observation notation, provenance, MOC creation all follow the rules above. Maintenance mode does not duplicate or contradict them.

### Mode Detection

Detect at the start of every cycle. First match wins:

1. `SLEEP_MODE=short-loop` or `SLEEP_MODE=full-session` in environment overrides everything.
2. `LOOP_INTERVAL_MINUTES <= 30` → `short-loop`.
3. Prior cycles exist in this session under `/loop` → `short-loop`.
4. Default: `full-session` (manual `/sleep`, GHA cron).

Log the detected mode and signal in the cycle summary.

### Phases

Full per-phase instructions in [[references/maintenance-phases]].

| Phase | Name                        |
| ----- | --------------------------- |
| 0     | Graph Health Baseline       |
| 1     | Session Backfill            |
| 2     | Transcript Mining           |
| 3     | Episode Replay              |
| 4     | Knowledge Consolidation     |
| 5     | Index Refresh               |
| 6     | Data Quality Reconciliation |
| 7     | Staleness Sweep             |
| 8     | Refile Processing           |
| 9     | Graph Maintenance           |
| 10    | Consolidation Self-Check    |
| 11    | Brain Sync                  |

[[references/maintenance-phases]] also contains: sub-agent dispatch rules (Phases 2, 4), halt surfacing protocol, pacing (short-loop vs full-session), cycle summary template, and consolidation PR process.

### CI Environment

When running on GitHub Actions, no PKB MCP server is available. Use `Bash`, `Glob`, `Grep`, `Read`, `Write`, `Edit` directly on markdown files. Changes sync to PKB consumers via git push. `Edit` is restricted to transcript frontmatter under `$AOPS_SESSIONS/` only — never inside `$ACA_DATA`.
