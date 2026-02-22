---
name: tools
title: Tools Index
type: index
category: framework
description: |
    Reference for MCP servers and standard tools available to the agent.
    Used by hydrator for routing decisions - what capabilities exist.
permalink: tools
tags: [framework, routing, tools, index]
---

# Tools Index

Reference for agent capabilities. Use this to understand what operations are possible.

## MCP Servers

| Server         | Purpose                    | Key Operations                                                         |
| -------------- | -------------------------- | ---------------------------------------------------------------------- |
| `omcp`         | Outlook email & calendar   | Search/read/draft messages, list events, create meetings               |
| `zot`          | Zotero research library    | Search papers, get citations, find similar works, OpenAlex integration |
| `osb`          | Meta Oversight Board cases | Search decisions, get case summaries, legal reasoning analysis         |
| `memory`       | Semantic knowledge store   | Store/retrieve memories, tag-based search, recall by time              |
| `pkb`          | Personal knowledge base    | Tasks, semantic search, knowledge graph, task network metrics          |
| `context7`     | Library documentation      | Look up API docs for any programming library                           |

<!-- NS: exclude Standard Tools from this file. -->

## Standard Tools

| Tool        | Purpose                |
| ----------- | ---------------------- |
| `Read`      | Read file contents     |
| `Write`     | Create new files       |
| `Edit`      | Modify existing files  |
| `Bash`      | Run shell commands     |
| `Glob`      | Find files by pattern  |
| `Grep`      | Search file contents   |
| `Task`      | Spawn subagents        |
| `WebFetch`  | Fetch web page content |
| `WebSearch` | Search the web         |

## Routing Hints

- **Email work** → `omcp` server has full Outlook access
- **Research/citations** → `zot` for library, `osb` for Oversight Board
- **Remember context** → `memory` server for semantic storage
- **Task management** → `pkb` for all work tracking, search, and knowledge graph
- **Documentation lookup** → `context7` for library APIs

## PKB Tool Usage (MANDATORY)

Task operations MUST use `mcp__pkb__*` tools. NEVER use `Read`/`Glob`/`Grep`/`Bash` on task files directly — direct filesystem access to `data/tasks/` is blocked by the enforcement hook.

| Operation | Use this tool | Do NOT use |
| --------- | ------------- | ---------- |
| Look up a task by ID | `mcp__pkb__get_task(id="aops-c4f7a17a")` | `Read("data/tasks/aops-c4f7a17a-*.md")` |
| Search for tasks | `mcp__pkb__task_search(query="...")` | `Glob("data/tasks/**/*.md")` |
| List tasks | `mcp__pkb__list_tasks(...)` | `Bash("ls data/tasks/")` |
| Get task context | `mcp__pkb__pkb_context(...)` | `Grep("data/tasks/**")` |

Task files in `data/tasks/` use the naming convention `<project>-<uid>-<slug>.md` (e.g. `aops-c4f7a17a-brain-repo-sync.md`). Always retrieve them via `mcp__pkb__get_task` or `mcp__pkb__task_search`, not by reading the filesystem.
