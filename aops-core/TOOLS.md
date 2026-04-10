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

## Core Server

| Server | Purpose                 | Key Operations                                           |
| ------ | ----------------------- | -------------------------------------------------------- |
| `pkb`  | Personal knowledge base | Tasks, semantic search, knowledge graph, memories, notes |

PKB is always available. See CONNECTORS.md for optional tool categories.

## Connector Categories

These are optional tools resolved at runtime. Skills reference them as `~~category`.

| Category         | Placeholder          | Purpose                                                        |
| ---------------- | -------------------- | -------------------------------------------------------------- |
| Email & calendar | `~~email`            | Search/read/draft messages, list events, create meetings       |
| Research library | `~~research-library` | Search papers, get citations, find similar works               |
| Case database    | `~~case-database`    | Search decisions, get case summaries, legal reasoning analysis |
| Documentation    | `~~documentation`    | Look up API docs for any programming library                   |
| AI assistant     | `~~ai-assistant`     | Delegate analysis to another AI model                          |
