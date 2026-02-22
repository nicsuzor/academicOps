---
title: PKB Server Specification
type: spec
status: draft
tags: [spec, pkb, mcp, cli, mem]
created: 2026-02-22
---

# PKB Server Specification

Combined CLI + MCP server for personal knowledge base operations.

**Implementation**: [mem](https://github.com/nictsuzor/mem) (Rust, `aops` CLI + `pkb-search` MCP server)

## Giving Effect

- `aops` CLI binary — direct terminal access
- `pkb-search` MCP server binary — agent access via stdio transport
- [[knowledge-management-philosophy]] — foundational design principles
- [[work-management]] — task lifecycle and graph insertion
- [[mcp-decomposition-tools-v2]] — "Dumb Server, Smart Agent" principle

## Users

### User 1: Nic (CLI)

Academic researcher with ADHD. Uses the CLI directly at terminal for:
- Quick searches ("what do I know about X?")
- Task triage ("what should I work on?")
- Creating tasks and notes during work
- Understanding task dependencies and blockers
- Graph exploration and maintenance

**Key constraint**: Working memory limitations. Answers must be immediate. Cognitive load must be minimal. The system remembers so the user doesn't have to.

### User 2: AI Agents (MCP)

Claude Code and Gemini agents operating in aops framework sessions. Use MCP tools for:
- Gathering context before executing work (search, task state)
- Managing work items (create, update, complete tasks)
- Capturing knowledge (create documents, memories)
- Understanding the work graph (dependencies, blockers, metrics)

**Key constraint**: Agents need raw data, not recommendations. Per "Dumb Server, Smart Agent" principle (P#78): deterministic computation in server, judgment in LLM.

## Foundational User Stories

Extracted from [[knowledge-management-philosophy]], [[tasks-mcp-server]], and [[task-state-index]].

### US1: Human-readable without tools

> I can open any file with a text editor and read it.

No lock-in. Files are markdown with YAML frontmatter. If the server dies, files remain fully usable. The server is an **overlay**, not a replacement.

### US2: Find by meaning, not location

> I think "what do I know about X?" not "where did I save X?"

Semantic search is the primary retrieval mechanism. Tags, types, and projects are secondary filters. The user should never need to know file paths.

### US3: One place for task state

> As an overwhelmed academic with ADHD, I want one place that knows what all my tasks are and what state they're in, so that I can trust it and build views/automations on top of it.

The PKB server is the single source of truth for task state. All task operations go through it. Format consistency is enforced. No state corruption.

### US4: Guaranteed task integrity

> I want guaranteed task state integrity through exclusive MCP-controlled write access, so that agents can't bypass scripts to corrupt task data.

All CRUD operations work reliably 100% of the time. Format consistency enforced. Fail-fast on malformed data. No silent failures.

### US5: Connected work graph

> Every task must be connected to the hierarchy: task -> epic -> chain -> project -> strategic priority.

Disconnected tasks are invisible to prioritisation. The server exposes graph topology so agents and humans can identify orphans, understand dependencies, and maintain structural integrity.

### US6: Capture everything, deliver just-in-time

> Capture comprehensively. Deliver precisely. Reduce cognitive load.

The server supports comprehensive capture (create documents, memories, tasks with minimal friction) and precise retrieval (semantic search, filters, graph traversal). It never proactively surfaces information — always query-driven.

### US7: Dumb server, smart agent

> The MCP server is a data access layer only. It exposes raw data structures that enable LLM agents to reason and make decisions.

The server computes deterministic metrics (counts, depths, degrees). It does NOT make recommendations, score by "value", generate proposals, or perform semantic analysis beyond vector similarity. Judgment stays in the LLM.

## MCP Tool Inventory (18 tools)

Target: 18 tools across 6 groups. Each tool has one clear purpose.

| # | Tool | Group | Purpose |
|---|------|-------|---------|
| 1 | `search` | Search | Hybrid semantic + graph-proximity search (primary search tool) |
| 2 | `task_search` | Search | Semantic search filtered to task/project/goal types |
| 3 | `get_document` | Search | Read full contents of a document by path |
| 4 | `list_documents` | Search | Browse/filter documents by tag, type, status, project |
| 5 | `list_tasks` | Task read | List tasks with filters (project, status, priority, assignee). Status filter supports `ready` (no unmet deps) and `blocked` (has unmet deps, includes blocker info). |
| 6 | `get_task` | Task read | Single task detail + all relationships (parent, children, depends_on, blocks). Always includes relationship context. |
| 7 | `get_network_metrics` | Task read | Centrality metrics for a node: PageRank, betweenness, degree, downstream weight |
| 8 | `create_task` | Task write | Create a new task. Params: title (required), id, parent, priority, project, tags, depends_on, assignee, complexity, body |
| 9 | `update_task` | Task write | Update frontmatter fields on existing task. Params: id or path, updates (object) |
| 10 | `complete_task` | Task write | Mark task as done. Sets status=done, re-indexes. |
| 11 | `create` | Document | Create any document type with enforced frontmatter. Routes to subdirectory by type. Params: title, type (required), plus optional metadata. |
| 12 | `create_memory` | Document | Create memory/note (future: episodic memories — short observations grouped as dot-point lists within existing files). Params: title (required), tags, body, memory_type, source |
| 13 | `append` | Document | Append timestamped content to existing document. Optionally target a section heading. |
| 14 | `delete` | Document | Delete document by ID (flexible resolution). |
| 15 | `pkb_context` | Graph | Full knowledge neighbourhood: metadata, backlinks by source type, nearby nodes within N hops |
| 16 | `pkb_trace` | Graph | Find shortest paths between two nodes in the knowledge graph |
| 17 | `pkb_orphans` | Graph | Find disconnected nodes with zero edges |
| 18 | `reindex` | Admin | Force full re-scan and rebuild of vector store + knowledge graph |

### Changes from current (v0.1.4)

| Change | Rationale |
|--------|-----------|
| `pkb_search` renamed to `search` | Primary search tool, clearer name |
| `semantic_search` removed | `search` subsumes it (hybrid is always better) |
| `get_ready_tasks` removed | `list_tasks(status="ready")` replaces it |
| `get_blocked_tasks` removed | `list_tasks(status="blocked")` replaces it, includes blocker info |
| `get_task_network` removed | `get_task` now always includes relationships |
| `create_document` renamed to `create` | Shorter, universal — creates any document type |
| `append_to_document` renamed to `append` | Shorter |
| `delete_document` renamed to `delete` | Shorter |

### Future research: episodic memories

`create_memory` may evolve to handle **episodic memories** — short observations or facts stored as dot-point lists grouped within existing markdown files, rather than one-file-per-memory. Research needed into optimal PKB structures for this pattern.

## Core Functions

### 1. Search & Retrieval

The primary job. "What do I know about X?"

| Function | CLI | MCP | Purpose |
|----------|-----|-----|---------|
| Search | `search <query>` | `search` | Hybrid semantic + graph-proximity search |
| Task search | — | `task_search` | Semantic search filtered to tasks |
| Get document | — | `get_document` | Full file contents |
| List/filter | `list` | `list_documents` | Browse by tag, type, status, project |

**Success criteria**:
- 80%+ of queries return relevant results in top 5
- Response time < 2 seconds
- User thinks "what do I know about X?" not "where did I save X?"

### 2. Task Management

Track work across sessions. "What needs doing? What's blocked?"

| Function | CLI | MCP | Purpose |
|----------|-----|-----|---------|
| List tasks | `tasks [ready\|blocked\|all]` | `list_tasks` | Task state with filters (project, status, priority, assignee) |
| Get task | `task <id>` | `get_task` | Task details + all relationships |
| Create task | `new <title>` | `create_task` | Add work item |
| Update task | `update <id>` | `update_task` | Change status, priority, etc. |
| Complete task | `done <id>` | `complete_task` | Mark done |
| Dependencies | `deps <id>` | (via `get_task`) | Dependency tree |
| Metrics | `metrics [id]` | `get_network_metrics` | PageRank, betweenness, downstream weight |

**Task lifecycle**:
```
active -> in_progress -> done
           |
        blocked/waiting
```

**Statuses**: `active`, `in_progress`, `blocked`, `waiting`, `done`, `cancelled`, `merge_ready`, `review`

**Success criteria**:
- All CRUD operations work reliably (>99% success rate)
- Format consistency enforced (frontmatter validation)
- Fail-fast on malformed data
- Zero state corruption

### 3. Document CRUD

Create and maintain knowledge artifacts. Notes, memories, insights.

| Function | CLI | MCP | Purpose |
|----------|-----|-----|---------|
| Create | `remember <title>` | `create`, `create_memory` | New document of any type |
| Append | `append <id> <content>` | `append` | Add timestamped content to existing document |
| Delete | `delete <id>` | `delete` | Remove document |

**Document types**: `task`, `bug`, `epic`, `feature`, `project`, `goal`, `note`, `knowledge`, `memory`, `insight`, `observation`

**Routing**: Documents auto-route to subdirectories by type (tasks/ projects/ goals/ notes/).

**Success criteria**:
- Frontmatter always valid YAML with required fields (id, title, type, created, modified)
- Files human-readable without tools (US1)
- Flexible ID resolution (by ID, filename stem, or title)

### 4. Knowledge Graph

Understand relationships and structure. "What depends on what? What's disconnected?"

| Function | CLI | MCP | Purpose |
|----------|-----|-----|---------|
| Context | `context <id>` | `pkb_context` | Full neighbourhood: backlinks, nearby nodes |
| Trace | `trace <from> <to>` | `pkb_trace` | Shortest paths between nodes |
| Orphans | `orphans` | `pkb_orphans` | Disconnected nodes |
| Metrics | `metrics [id]` | `get_network_metrics` | PageRank, betweenness, degree, downstream weight |
| Export | `graph --format F` | — | Export graph (JSON, GraphML, DOT) |

**Edge types**: `DependsOn` (hard blocking), `SoftDependsOn` (informational), `Parent` (hierarchy), `Link` (wikilink references)

**Success criteria**:
- Graph reflects all wikilinks and frontmatter relationships
- Metrics are deterministic and reproducible
- Orphan detection catches all disconnected nodes

### 5. Index Management

Keep the index in sync with files on disk.

| Function | CLI | MCP | Purpose |
|----------|-----|-----|---------|
| Reindex | `reindex [--force]` | `reindex` | Full re-scan + rebuild |
| Status | `status` | — | Document count, DB size |
| Add | `add <files>` | — | Add specific files |

## CLI vs MCP Boundary

The CLI and MCP server share the same core engine but have different affordances:

| Aspect | CLI | MCP |
|--------|-----|-----|
| **Audience** | Human at terminal | AI agent in session |
| **Output** | Formatted text, tables, trees | Structured JSON |
| **Graph export** | Yes (`graph` command) | No (agent doesn't need it) |
| **Hybrid search** | No (human uses `search`) | Yes (`pkb_search` with graph boost) |
| **Task search** | No (human uses `tasks`) | Yes (`task_search` for semantic filtering) |
| **Batch operations** | No (one at a time) | No (one at a time) |

**Principle**: CLI optimises for human scanning (tree views, colour, truncation). MCP optimises for machine parsing (full data, structured output).

## Data Format

### Files

All PKB files are markdown with YAML frontmatter. This is non-negotiable (US1).

```yaml
---
id: unique-identifier
title: Human-readable title
type: task|note|knowledge|memory|insight|...
created: 2026-02-22T10:00:00Z
modified: 2026-02-22T10:00:00Z
alias: [resolution-keys]
permalink: same-as-id
# Optional:
status: active
priority: 0-4
project: project-name
tags: [tag1, tag2]
assignee: nic|bot
depends_on: [other-id]
parent: parent-id
---

Markdown body content.
```

### Vector Store

Binary vector database at `$ACA_DATA/pkb_vectors.bin`. Contains MiniLM-L6-v2 embeddings (384 dimensions). This is a derived cache — can be rebuilt from files at any time.

### Knowledge Graph

In-memory graph built from frontmatter relationships and wikilinks on each startup/reindex. Not persisted separately — rebuilt from files.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `ACA_DATA` | `~/brain` | PKB root directory (the files) |
| `RUST_LOG` | `info` | Log level |
| `AOPS_OFFLINE` | `false` | Disable model auto-download |

## Non-Goals

- **AI-powered recommendations** — server returns data, agents make judgments
- **Proactive notifications** — always query-driven (US6)
- **Database as source of truth** — files are the data, index is derived (US1)
- **Multi-user** — single-user system
- **Web UI** — CLI and MCP only
- **Email/calendar integration** — handled by other MCP servers (outlook-mcp)

## Design Decisions

### D1: CLI task-specific search — No

`aops tasks` with `--project` filtering covers "what needs doing". Human scans `aops search` results visually. Agent gets `task_search`. No CLI equivalent needed.

### D2: MCP tool consolidation — 22 down to 18

Merged `get_ready_tasks` and `get_blocked_tasks` into `list_tasks` with status filters. Merged `get_task_network` into `get_task` (always include relationships). Consolidated `pkb_search`/`semantic_search` into single `search`. Shortened names (`create_document` -> `create`, etc.).

### D3: Keep `create_memory` separate from `create`

`create` is the universal document creator. `create_memory` stays separate because it may evolve for episodic memory patterns (dot-point observations within existing files). See "Future research" section.

### D4: No `--json` CLI output — not now

MCP serves the machine-readable need. `--json` for shell scripting is low priority. Add later if demand arises.

### D5: Search graph boost — implicit via boost_id

`search` with no `boost_id` = pure vector search. `search` with `boost_id=<node>` = hybrid (semantic + graph proximity). No separate flag needed. Clean API, no change required.

### D6: Blocker info — inline per task

When `list_tasks(status="blocked")`, each task includes a `blocked_by` array with blocker details (id, title, status). Consistent with how `get_task` returns relationships. Agent sees *why* a task is blocked without a second lookup.

## Relationship to Legacy Systems

This project replaces:
- Python task scripts (`task_add.py`, `task_view.py`, `task_archive.py`, `task_update.py`)
- Python task index regeneration (`regenerate_task_index.py`)
- The `mcp__plugin_aops-core_task_manager__*` tools (Python FastMCP server)

It does NOT replace:
- Memory MCP server (`mcp__memory__*`) — separate semantic memory with HTTP transport
- Zotero MCP server (`mcp__zot__*`) — academic reference management
- Outlook MCP server (`mcp__outlook__*`) — email/calendar
