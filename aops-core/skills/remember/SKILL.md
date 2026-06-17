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
allowed-tools: mcp__pkb__create,mcp__pkb__create_memory,mcp__pkb__append,mcp__pkb__get_document,mcp__pkb__search,mcp__pkb__update_task,Bash,Read,Write,Grep,Glob,Edit,Skill,mcp__pkb__pkb_orphans,mcp__pkb__list_tasks,mcp__pkb__graph_stats,mcp__pkb__get_stats,mcp__pkb__get_network_metrics,mcp__pkb__get_task,mcp__pkb__task_search,mcp__pkb__pkb_context,mcp__pkb__batch_reparent,mcp__pkb__find_duplicates,mcp__pkb__batch_merge,mcp__pkb__merge_node,mcp__pkb__complete_task,mcp__pkb__batch_reclassify,mcp__pkb__batch_archive,mcp__pkb__batch_update,mcp__pkb__create_task,mcp__pkb__update_memory,mcp__omcp__messages_search,mcp__omcp__messages_query,mcp__omcp__calendar_list_events
owner: pauli
version: 4.1.0
---

# Memory Skill

Provides domain instructions for knowledge capture, persistence, and maintenance in the PKB (`$ACA_DATA`).

## Immediate Mode (`/remember`)

### Invariants

- Do not use `Write` or `Edit` on files under `$ACA_DATA/`. Use the PKB MCP toolset.
- Use `mcp__pkb__search` for semantic discovery. Do not use `Glob` or `Grep` on `$ACA_DATA/`.

### Hard Rules

- `mcp__pkb__create`: Create a document (projects, contexts, meeting notes).
- `mcp__pkb__create_memory`: Add a memory/note.
- `mcp__pkb__append`: Extend an existing document.
- `mcp__pkb__get_document`: Read a document.
- `mcp__pkb__search`: Search before creating new content — and before asserting a fact. Don't assume; look it up.

### Curation

- Capture episodic records accurately in the moment.
- Curate and synthesize knowledge inline as decisions or patterns emerge; do not defer all synthesis to the maintenance loop.

### Storage and File Locations

| Content                | Tool                                                  | Target                              |
| :--------------------- | :---------------------------------------------------- | :---------------------------------- |
| **Epics/projects**     | `mcp__pkb__create(type="epic"\|"project")`            | `projects/`                         |
| **Tasks/issues**       | `gh issue create` (GitHub primary)                    | Synced automatically                |
| **Durable knowledge**  | `mcp__pkb__create` or `mcp__pkb__create_memory`       | `knowledge/`, `context/`            |
| **Session findings**   | `mcp__pkb__update_task` on parent task                | Task body                           |
| **Axioms/framework**   | `/framework` skill — do NOT write to `brain/context/` | `skills/` via framework workflow    |
| **Context/goals**      | `mcp__pkb__create`                                    | `context/`, `goals/`                |
| **Meeting/call notes** | `mcp__pkb__create(type="meeting-note")`               | `knowledge/<topic>/` or `projects/` |
| **Sessions/daily**     | `mcp__pkb__create(type="daily-note")`                 | `sessions/`                         |

**Episodic classification:** Operational records (agent activity, debug logs) → update parent task body only; do not create `$ACA_DATA/` docs. Durable episodic (meeting notes, user daily notes) → save to `$ACA_DATA/` with correct type frontmatter.

## Canonical Topic Notes (Enduring Memory)

Maintain exactly **one canonical note per first-class topic** (tools, projects, skills, agents, concepts).

- Update existing notes with `mcp__pkb__append`. Create new notes only when the topic does not exist.
- Avoid one-off observation files.

### Reconciliation

Search for duplicate or peer notes during updates. Merge unique content, retire weaker versions, update wikilinks. Delete superseded files — do not leave `superseded_by:` pointers; follow [[consolidation-procedure]] Step 3.

## Workflow

1. **Search**: `mcp__pkb__search(query="topic")`.
2. **Evaluate**: If a canonical note exists, append to it. Do not create a separate file.
3. **Write**: Call `mcp__pkb__create(title, body, type, tags)` or `mcp__pkb__create_memory(title, body, tags)`.

## Graph Integration

- Every note must contain at least one `[[wikilink]]` to a parent concept, project, goal, or entity in prose.
- Link all proper nouns; provide markdown links for external issues and PRs (e.g., `[org/repo#123](url)`).
- List semantic relationships in a `## Relationships` section: `- [related] [[task-id]] — description`.
- **Wikilinks**: prose only — never inside code blocks, inline code, or technical tables. No standalone "See Also" section.
- **Abstraction**: Capture generalizable patterns, not local implementation details.
- **Observation callouts** (required for factual claims in episodic notes):
  ```
  > [!observation] Factual statement
  > Source: [[source-note]]
  > Confidence: <0.0–1.0>  (≥0.8 established · 0.4–0.79 provisional · <0.4 speculative)
  ```
  If a new observation contradicts an existing one, record both with sources and flag. Do not overwrite silently.
- **`type: knowledge` provenance** (required): `sources:`, `synthesized:`, `last_reviewed:`, `confidence:`, `maturity: seedling|budding|evergreen`.
- **MOCs**: Create when a topic has 5+ notes; use `type: moc`, `tags: [moc, topic-area]`, `created:`, `last_reviewed:`.

## Background Capture

To capture asynchronously, spawn a `model="haiku"` background agent with `run_in_background=true` and prompt it to invoke `Skill(skill='remember')` with the content.

## Output Expectations

State PKB write details directly: tool used, note title, returned ID. Do not expose raw filesystem paths.

## Maintenance Mode (`/sleep`)

The canonical home of the former `/sleep` skill. Runs periodic offline consolidation on a GHA workflow or manual trigger.

### Triggers

Invoke Maintenance Mode on: explicit `/sleep` call; GHA schedule or `workflow_dispatch`; or `SLEEP_MODE` env var set.

### Rules

- Never fabricate assertions without provenance.
- Do not edit daily notes, meeting notes, or task bodies (except adding `consolidated: YYYY-MM-DD` in frontmatter).
- Record and preserve contradictions.

### Mode Detection

First match determines mode:

1. `SLEEP_MODE` env var overrides (`short-loop` | `full-session`).
2. `LOOP_INTERVAL_MINUTES <= 30` → `short-loop`.
3. Prior cycles ran in this session → `short-loop`.
4. Default → `full-session`.

### Maintenance Phases

See [[references/maintenance-phases]] for sub-agent rules, pacing, and exit protocols.

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

On GitHub Actions, no PKB MCP is available. Use direct file operations (`Bash`, `Glob`, `Grep`, `Read`, `Write`, `Edit`) on markdown files. Do not edit files outside `$AOPS_SESSIONS/` (except git commits/push).
