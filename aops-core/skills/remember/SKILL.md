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

Provides domain instructions for knowledge capture, persistence, and maintenance in the Personal Knowledge Base (PKB) (`$ACA_DATA`).

## Immediate Mode (`/remember`)

### Invariants

- Do not use `Write` or `Edit` on files under `$ACA_DATA/`. Use the PKB MCP toolset.
- Use `mcp__pkb__search` for semantic discovery. Do not use `Glob` or `Grep` on `$ACA_DATA/`.

### Hard Rules

- `mcp__pkb__create`: Create a document (projects, contexts, meeting notes).
- `mcp__pkb__create_memory`: Add a memory/note.
- `mcp__pkb__append`: Extend an existing document.
- `mcp__pkb__get_document`: Read a document.
- `mcp__pkb__search`: Search before creating new content.

### Curation

- Capture episodic records accurately in the moment.
- Curate and synthesize knowledge inline as decisions or patterns emerge; do not defer all synthesis to the `/sleep` loop.

### Storage Hierarchy

| Content               | Write Via                                       | Target Location          |
| :-------------------- | :---------------------------------------------- | :----------------------- |
| **Epics/projects**    | `mcp__pkb__create(type="epic"\|"project")`      | `projects/`              |
| **Tasks/issues**      | `gh issue create` (GitHub primary)              | Synced automatically     |
| **Durable knowledge** | `mcp__pkb__create` or `mcp__pkb__create_memory` | `knowledge/`, `context/` |
| **Session findings**  | `mcp__pkb__update_task` on parent task          | Task body                |

### File Locations

| Content                | Location                            | Notes                                 |
| :--------------------- | :---------------------------------- | :------------------------------------ |
| Project metadata       | `projects/<name>.md`                | Hub files. Hub-doc type is `epic`.    |
| Project details        | `projects/<name>/`                  | Subdirectory.                         |
| Goals                  | `goals/`                            | Strategic objectives.                 |
| Context (about user)   | `context/`                          | User preferences, history.            |
| Sessions/daily         | `sessions/`                         | Daily notes only, `type: daily-note`. |
| General knowledge      | `knowledge/<topic>/`                | Durable facts (non-user).             |
| Meeting/call notes     | `knowledge/<topic>/` or `projects/` | `type: meeting-note`.                 |
| Maps of Content (MOCs) | `knowledge/` or topic subdirs       | Navigational hubs, `type: moc`.       |

### Episodic Classification

- **Operational episodic** (agent activity, debugging logs, experimental steps) -> Update parent task body using tasks MCP tools. Do not create new documents in `$ACA_DATA/`.
- **Durable episodic** (meeting notes, user daily notes) -> Save to `$ACA_DATA/` with correct type frontmatter.

## Canonical Topic Notes (Enduring Memory)

Maintain exactly **one canonical note per first-class topic** (tools, projects, skills, agents, concepts).

- Update existing topic notes using `mcp__pkb__append` in the relevant section.
- Create new canonical notes with a standard section scaffold (e.g., `Overview`, `Usage`, `Known Issues`) only if the topic does not exist.
- Avoid creating one-off observation files.

### Reconciliation

During updates, search for duplicate or peer notes. Merge unique content, retire weaker versions (delete or set `superseded_by: [[canonical-id]]`), and update wikilinks.

## Workflow

1. **Search**: Search PKB first: `mcp__pkb__search(query="topic")`.
2. **Evaluate**: If a canonical note exists, append to it. Do not create a separate file.
3. **Write**: Call the appropriate PKB MCP tool:

```json
mcp__pkb__create(
  title="Descriptive Title",
  body="Content with [[wikilinks]].",
  type="note" | "project" | "epic" | "knowledge" | "moc" | "meeting-note",
  tags=["tag1", "tag2"]
)
```

Or for lightweight facts:

```json
mcp__pkb__create_memory(
  title="descriptive title",
  body="content",
  tags=["tag1"]
)
```

## Graph Integration

### Links and References

- Every note must contain at least one [[wikilink]] to a parent concept, project, goal, or entity in prose.
- Link all proper nouns.
- Provide explicit markdown links for external issues and PRs (e.g., `[org/repo#123](url)`).
- List semantic relationships in a `## Relationships` section:
  ```markdown
  ## Relationships

  - [related] [[task-id]] — description
  - [upstream-bug] [org/repo#123](url)
  ```
- **Wikilink Conventions**: Add wikilinks only in prose. Never put them inside code blocks, inline code, or technical tables. Do not create a standalone "See Also" section.

### Abstraction Level

For framework tasks, capture generalizable patterns (e.g., "Configuration should be set once at initialization") rather than local implementation details.

### Observation Notation

Factual claims in episodic notes must be formatted as Obsidian callouts:

```markdown
> [!observation] Factual statement
> Source: [[source-note]]
> Confidence: <numeric value 0.0 to 1.0>
```

- Numeric confidence mappings (include numeric value in frontmatter):
  - `established` (>= 0.8): verified, multiple sources.
  - `provisional` (0.4 - 0.79): limited evidence.
  - `speculative` (< 0.4): inference.
- If a new observation contradicts an existing one, record both with sources. Do not overwrite silently.

### Provenance (Required for `type: knowledge`)

Include these frontmatter fields:

- `sources:` (YAML list)
- `synthesized:` (ISO date)
- `last_reviewed:` (ISO date)
- `confidence:` (numeric 0.0 - 1.0)
- `maturity:` `seedling` | `budding` | `evergreen`

## Maps of Content (MOCs)

Use MOCs to index and curate links to related notes when a topic area grows to 5+ notes.

### MOC Frontmatter

```yaml
title: "MOC: Topic Name"
type: moc
tags: [moc, topic-area]
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
```

## Background Capture

To capture memories asynchronously:

```json
Task(
  subagent_type="general-purpose", model="haiku",
  run_in_background=true,
  description="Remember: [summary]",
  prompt="Invoke Skill(skill='remember') to persist: [content]"
)
```

## Output Expectations

State the PKB write details directly and concisely:

- Tool used
- Title of note
- ID / permalink (returned by PKB)
  _Do not expose raw local filesystem paths._

## Maintenance Mode (`/sleep`)

Runs periodic offline consolidation on a GHA workflow or manual trigger.

### Rules

- Never fabricate assertions without provenance.
- Do not edit daily notes, meeting notes, or task bodies (except adding `consolidated: YYYY-MM-DD` in frontmatter).
- Record and preserve contradictions.

### Mode Detection

First match determines mode:

1. Environment variable `SLEEP_MODE` overrides default (`short-loop` | `full-session`).
2. `LOOP_INTERVAL_MINUTES <= 30` -> `short-loop`.
3. If prior cycles ran in this session -> `short-loop`.
4. Default -> `full-session`.

### Maintenance Phases

See [[references/maintenance-phases]] for detailed sub-agent rules, pacing, and exit protocols.

| Phase | Name                        |
| :---- | :-------------------------- |
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

### CI Environment Constraints

When running on GitHub Actions, no PKB MCP server is available. Direct file tool operations (`Bash`, `Glob`, `Grep`, `Read`, `Write`, `Edit`) on markdown files are allowed. Do not edit files outside `$AOPS_SESSIONS/` (except git commits/push).
