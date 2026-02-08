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
| `task_manager` | Work tracking system       | Create/update/complete tasks, manage dependencies, task trees          |
| `context7`     | Library documentation      | Look up API docs for any programming library                           |

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
- **Task management** → `task_manager` for all work tracking
- **Documentation lookup** → `context7` for library APIs
