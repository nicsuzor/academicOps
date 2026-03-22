---
title: "PKB Episodic Content Model: Observations, Logs, and the Semantic/Episodic Divide"
type: spec
status: draft
created: 2026-03-22
tags:
  - pkb
  - episodic
  - memory
  - knowledge-management
  - architecture
---

# PKB Episodic Content Model: Observations, Logs, and the Semantic/Episodic Divide

## Problem

The `/remember` skill currently declares `$ACA_DATA` as containing "ONLY semantic memory - timeless truths, always up-to-date" and routes all episodic content to the tasks MCP. This is wrong in two ways:

1. `$ACA_DATA` already contains episodic files (`type: daily`, `type: session-log`, meeting notes, reading reviews) — the "semantic only" rule is violated in practice and always will be.
2. The tasks MCP is for **work items** (things with actionable status, lifecycle, and graph hierarchy). Diary entries, meeting notes, field observations, and reading notes are not tasks — they have no lifecycle, no status, and no place in the work graph. Stuffing them into task bodies creates noise, breaks task management, and misrepresents their purpose.

The result is a gap: a class of legitimate PKB content — **episodic records** — has no clear home, no consistent format, and no coherent vectorization strategy.

## Research Background

### PKM literature consensus (Zettelkasten, BASB, Evergreen Notes)

The canonical three-tier model from Ahrens/Matuschak/Forte converges on:

| Tier | Name                  | Character                       | Fate                                        |
| ---- | --------------------- | ------------------------------- | ------------------------------------------- |
| 1    | Fleeting / capture    | Raw, ephemeral, time-stamped    | Processed within days; archived or promoted |
| 2    | Permanent / evergreen | Atomic, synthesized, timeless   | Maintained indefinitely; the knowledge core |
| 3    | Index / MOC           | Cluster summaries, entry points | Curated navigation layer                    |

**Key tension**: Temporal/episodic content (journals, logs, meeting notes) doesn't fit cleanly into this model. These PKM systems treat them as "inboxes" to be processed — but in practice they accumulate faster than they are processed. The episodic archive grows; the semantic layer stagnates.

### What the research says about this system specifically

The `sleep-cycle.md` spec correctly identifies the problem: "We have write-optimised storage that captures observations well but is terrible for retrieval." The sleep cycle proposes a consolidation pipeline (episode replay → promotion candidates) but acknowledges the unsolved detection problem: how do you know what's worth promoting?

The answer from the Zep temporal knowledge graph architecture (arxiv:2501.13956): **keep episodic content permanently as first-class search citizens**, with temporal metadata, rather than treating them as inputs to be consumed and discarded. Episodic records have direct retrieval value — a search for "what was discussed with X about Y" legitimately targets the meeting note, not a synthesis of it.

### Chunking implications

The PKB currently uses whole-file embedding. This works well for the 200-word atomic note constraint on semantic files. For episodic files:

- **One file per episodic entry** (one meeting note, one diary entry): files stay small enough for whole-file embedding. Retrieval targets the correct entry. **This is the correct approach.**
- **Multiple entries aggregated in one file** (e.g., "all observations about project X over six months"): whole-file embedding averages across all entries, degrading retrieval precision for any specific one. Requires sub-document chunking that the PKB does not currently implement.

**Recommendation**: Preserve the one-file-per-entry pattern for episodic records. Group by topic directory, not by time. Avoid aggregated log files unless sub-document chunking is implemented.

---

## Revised Content Model

### What $ACA_DATA actually is

`$ACA_DATA` is the **personal knowledge corpus** — all persistent, personal knowledge artifacts that have been deliberately kept. It is not a "semantic-only" store. It contains:

- **Episodic records**: Time-stamped content kept verbatim for reference (diary, meetings, observations)
- **Synthesized knowledge**: Timeless, atomic, maintained notes (the "semantic memory" tier)
- **Navigation/index**: Maps of content, project hubs, MEMORY.md

What does NOT live in `$ACA_DATA`:

- Active work items → tasks MCP (lifecycle + graph operations)
- Raw unreviewed session transcripts → `sessions/transcripts/` (may or may not be indexed)

### Four-tier content model

```
Tier 0: Raw capture (ephemeral)
  ├── Session transcripts
  ├── Email captures
  └── Draft task bodies
  → Lives in: tasks (work items), sessions/transcripts/
  → Not persistently vector-indexed; processed and discarded or promoted

Tier 1: Episodic records (time-stamped, kept verbatim)
  ├── Daily notes
  ├── Meeting notes
  ├── Field observations
  └── Reading/review notes
  → Lives in: $ACA_DATA/ (see routing table below)
  → Vector-indexed as atomic files with temporal metadata
  → NOT synthesised unless a specific promotion trigger fires

Tier 2: Synthesized knowledge (timeless, atomic, maintained)
  ├── knowledge/ (facts, concepts)
  ├── context/ (user preferences, biographical)
  └── projects/, goals/ (strategic state)
  → Lives in: $ACA_DATA/
  → Vector-indexed; maintained and updated when superseded
  → Max 200 words per file for optimal embedding

Tier 3: Navigation / index
  ├── MEMORY.md (session-start index)
  ├── Maps of Content (MOCs)
  └── Project hub files
  → Lives in: $ACA_DATA/
  → Not primarily a search target; used for navigation
```

### Routing table

| Content type           | Characteristics                                 | Lives in                                               | Type                 |
| ---------------------- | ----------------------------------------------- | ------------------------------------------------------ | -------------------- |
| Work to do             | Has status, lifecycle, dependencies             | Tasks MCP                                              | `task`/`project`/etc |
| Observational tracking | Like a task but not actionable                  | Tasks MCP                                              | `learn`              |
| Daily note             | Capture + reflection + tasks for the day        | `$ACA_DATA/sessions/YYYY-MM-DD.md`                     | `daily`              |
| Meeting notes          | What was discussed, decisions, actions          | `$ACA_DATA/meetings/YYYY-MM-DD-topic.md`               | `note`               |
| Diary/journal entry    | Personal reflection, not work-focused           | `$ACA_DATA/journal/YYYY-MM-DD.md`                      | `note`               |
| Field observation      | Time-stamped observation about a specific topic | `$ACA_DATA/<project>/observations/YYYY-MM-DD-topic.md` | `note`               |
| Reading/review note    | Extracted ideas from a source                   | `$ACA_DATA/reviews/<slug>.md`                          | `review`             |
| Research finding       | Synthesized fact from a source                  | `$ACA_DATA/knowledge/<topic>/<slug>.md`                | `knowledge`          |
| Concept note           | Timeless, atomic, developed idea                | `$ACA_DATA/knowledge/<topic>/<slug>.md`                | `knowledge`          |
| User context           | Preferences, biographical, persistent           | `$ACA_DATA/context/<topic>.md`                         | `note`               |
| Project state          | Strategic-level project status                  | `$ACA_DATA/projects/<name>.md`                         | `project`            |
| Navigation hub         | Entry point, links to content                   | `$ACA_DATA/<dir>/index.md`                             | `index`              |

### Episodic record format

All episodic records use a common pattern:

```markdown
---
title: "Meeting: Topic with Person (YYYY-MM-DD)"
type: note
date: YYYY-MM-DD
tags: [meeting, project-name]
---

# Meeting: Topic with Person (YYYY-MM-DD)

Content.

## Decisions

- [[decision or outcome]]

## Actions

- Task → [[person responsible]]
```

Key requirements:

- `date:` frontmatter field (enables temporal search filtering)
- File name includes date prefix (enables sorting and navigation)
- Single entry per file (enables whole-file embedding)
- Links to relevant semantic notes (enables graph traversal)

---

## Vectorization and Chunking Strategy

### Current state

The PKB embeds whole files as single vectors. This is correct for the 200-word semantic note constraint. It degrades for longer content.

### Per-tier strategy

| Tier                 | Chunking approach   | Rationale                                  |
| -------------------- | ------------------- | ------------------------------------------ |
| Tier 0 (raw capture) | Not indexed         | Ephemeral; not for retrieval               |
| Tier 1 (episodic)    | Whole file          | One entry per file; fits embedding context |
| Tier 2 (semantic)    | Whole file          | 200-word max constraint; single concept    |
| Tier 3 (navigation)  | Excluded or partial | Navigation, not content                    |

### When sub-document chunking becomes needed

If the PKB acquires files that aggregate multiple episodic entries (e.g., an automatically-appended observation log), section-level chunking will be needed — splitting on H2/H3 headings with ~10% overlap. This is **not currently implemented** and should be a prerequisite for any design that accumulates entries within a single file.

**The simpler path**: Keep one entry per file. Let the file system organize by directory. Semantic search handles retrieval.

### Temporal metadata for search

A recurring problem: semantic search returns stale episodic content equally alongside recent content. Meeting notes from 18 months ago are retrieved alongside last week's notes.

**Near-term**: The `date:` frontmatter field should be used as a filter parameter in `pkb search`. Allow `--since YYYY-MM-DD` and `--before YYYY-MM-DD` filters that combine with semantic similarity.

**Longer-term**: Semantic documents (Tier 2) should carry a `valid_until:` field for time-sensitive facts. The sleep cycle staleness sweep should flag documents where `valid_until` has passed.

---

## Problems with the Current `/remember` Skill

### 1. False premise: "ONLY semantic memory"

**Current**: "`$ACA_DATA` contains ONLY semantic memory - timeless truths, always up-to-date"

**Problem**: False. `$ACA_DATA` already contains daily notes (`type: daily`), session logs, review notes, and meeting notes — all episodic. The rule has never been accurate and creates confusion.

**Fix**: Replace with accurate description: `$ACA_DATA` is the personal knowledge corpus. It contains episodic records, synthesized knowledge, and navigation files. The distinction is WHERE within `$ACA_DATA` content lives and how it is maintained.

### 2. Episodic routing to tasks MCP is wrong for non-work content

**Current**: "If it has a timestamp or describes agent activity, it's episodic → tasks MCP"

**Problem**: This collapses two distinct things:

- **Agent activity** (what the agent did, found, decided during a work session) → correctly belongs in task bodies
- **Human episodic records** (diary entries, meeting notes, observations) → these are NOT tasks and don't belong in the tasks MCP

Meeting notes stuffed into task bodies: lose structure, have wrong lifecycle, pollute task search.

**Fix**: Add a second routing branch for non-task episodic content → `$ACA_DATA/meetings/`, `$ACA_DATA/journal/`, etc.

### 3. No guidance on meeting notes

There is currently no canonical answer to "where do meeting notes go?" This leads to inconsistent storage across `sessions/`, `projects/`, loose files, and task bodies.

**Fix**: Explicit guidance: meeting notes go to `$ACA_DATA/meetings/YYYY-MM-DD-topic.md`, `type: note`, with `date:` frontmatter.

### 4. The synthesis pressure is premature

**Current**: "Observations accumulate in tasks → patterns emerge → synthesize to semantic docs"

**Problem**: This implicitly treats episodic records as temporary inputs to be consumed. In practice, the synthesis step rarely happens, leaving orphaned episodic content in task bodies with no synthesis.

**Fix**: Decouple: episodic records have permanent value on their own. Synthesis is a bonus, not a requirement. Meeting notes, observations, and diary entries are worth keeping regardless of whether they get synthesized into evergreen notes.

---

## Revised Decision Tree for /remember

```
What is this content?

├── Agent activity during a work session?
│   (what the agent did, found, tried, decided)
│   → YES: Update task body via tasks MCP. NOT this skill.
│
├── A work item to be done?
│   (has actionable status, lifecycle, dependencies)
│   → YES: Create/update task via tasks MCP. NOT this skill.
│
├── Observational tracking of a pattern?
│   (like a task but not actionable — monitoring something)
│   → YES: Create learn-type task via tasks MCP. NOT this skill.
│
├── A meeting, diary entry, or field observation?
│   (time-stamped, kept verbatim, human-authored)
│   → YES: Write to $ACA_DATA as episodic record.
│          meetings/ → YYYY-MM-DD-topic.md
│          journal/ → YYYY-MM-DD.md
│          <project>/observations/ → YYYY-MM-DD-topic.md
│          type: note, date: YYYY-MM-DD
│
├── A reading note or literature annotation?
│   (extracted ideas from a specific source)
│   → YES: Write to $ACA_DATA/reviews/<slug>.md
│          type: review
│
├── About the framework (axioms, heuristics, conventions)?
│   → YES: HALT and invoke /framework skill.
│
├── A synthesized, timeless fact or concept?
│   → YES: Write to $ACA_DATA/knowledge/<topic>/<slug>.md
│          type: knowledge, max 200 words
│
└── About the user (projects, goals, preferences)?
    → YES: Use appropriate location:
           context/ — persistent preferences and biographical
           projects/ — strategic state
           goals/ — strategic objectives
```

---

## Open Questions

### Q1: `create_memory` API evolution

The pkb-server-spec notes that `create_memory` "may evolve to handle episodic memories — short observations or facts stored as dot-point lists grouped within existing markdown files." This is attractive for reducing file proliferation, but requires sub-document chunking to search effectively.

**Decision needed**: Should we implement sub-document chunking (section-level, by H2 heading) in the PKB, or commit to the one-file-per-entry model to avoid the complexity?

Recommendation: defer the aggregated-entries model until sub-document chunking is implemented. Use one file per entry for now.

### Q2: Temporal filtering in search

Should `pkb search` support `--since` / `--before` parameters? Would require the PKB to index `date:` frontmatter and apply it as a pre-filter before semantic scoring.

Recommendation: yes — this is high value for episodic content retrieval and relatively low implementation cost.

### Q3: Synthesis triggers

How do we detect when episodic content warrants promotion to synthesized knowledge? The sleep cycle spec identifies this as unsolved.

Candidate triggers:

- The same pattern appears in 3+ task bodies or meeting notes (recurrence detection)
- An agent fails to find synthesized knowledge that would answer a specific query (retrieval failure signal)
- Human explicitly marks a note as a synthesis candidate

Recommendation: start with manual cues (tag `#synthesis-candidate`) and address automated detection in the sleep cycle spec.

### Q4: Vectorization of daily notes

Daily notes (`type: daily`, `$ACA_DATA/sessions/`) are currently excluded from sync per the sync spec ("Exclude: Daily notes outside `$ACA_DATA`"). But daily notes IN `$ACA_DATA/sessions/` are included. Should they be?

Daily notes typically include task lists, diary entries, and captures — heterogeneous content that embeds poorly as a single vector. They're better navigated than searched.

Recommendation: exclude daily notes from vector indexing by default (`sync: false` in frontmatter). Their content that warrants semantic retrieval should be promoted to knowledge notes or meeting notes.

---

## Summary of Proposed Changes

### To `/remember` skill (SKILL.md)

1. Remove "ONLY semantic memory" claim; replace with accurate content model
2. Add episodic records as a first-class routing destination
3. Update decision tree (see above)
4. Add file location rows for `meetings/`, `journal/`, `observations/`
5. Clarify "tasks MCP" routing applies to agent activity and work items, not all episodic content

### To `/workspace/specs/pkb-server-spec.md`

1. Update "Future research: episodic memories" to reflect this spec as the design resolution
2. Note the one-file-per-entry recommendation over aggregated dot-point lists
3. Add temporal filtering (`--since`/`--before`) as a near-term feature request

### New conventions

1. Meeting notes: `$ACA_DATA/meetings/YYYY-MM-DD-topic.md`, `type: note`, `date:` required
2. Journal: `$ACA_DATA/journal/YYYY-MM-DD.md`, `type: note`, `date:` required
3. Observations (project-linked): `$ACA_DATA/<project>/observations/YYYY-MM-DD-topic.md`
4. Daily notes: `sync: false` unless specific content has been promoted

---

## Relationships

- [related] [[pkb-server-spec]] — creates context for `create_memory` evolution
- [related] [[pkb-type-taxonomy]] — `note` type covers episodic records; `date:` field needed
- [related] [[sleep-cycle]] — consolidation pipeline from episodic to semantic
- [related] [[remember-skill]] — primary consumer of this spec's decisions
