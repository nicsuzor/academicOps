---
name: connectors
title: Connector Categories
type: reference
category: framework
description: |
    Maps abstract tool categories to concrete MCP servers.
    Skills reference categories (~~email, ~~research-library, etc.) rather than
    specific tools, making the plugin portable across different tool configurations.
permalink: connectors
tags: [framework, tools, connectors, configuration]
---

# Connectors

## How tool references work

Plugin files use `~~category` as a placeholder for whatever tool the user
connects in that category. Skills describe workflows in terms of categories
rather than specific products, so the same plugin works whether you use
Outlook or Gmail, Zotero or Mendeley.

When you see `~~email` in a skill instruction, it means "use whatever email
tool is available." The agent resolves this at runtime based on the MCP
servers currently connected.

## Core server (always required)

| Server | Purpose | Package |
|--------|---------|---------|
| `pkb`  | Personal knowledge base — tasks, semantic search, knowledge graph, memories, notes | [nicsuzor/mem](https://github.com/nicsuzor/mem) (Rust) |

PKB is the framework's core data layer. It is always referenced by name, not
as a connector category.

## Connector categories

| Category | Placeholder | Purpose | Example tools |
|----------|-------------|---------|---------------|
| Email & calendar | `~~email` | Read, draft, search, archive messages; list and create calendar events | Outlook (omcp), Gmail, Fastmail |
| Research library | `~~research-library` | Search papers, get citations, find similar works, discover new literature | Zotero (zot), Mendeley, Paperpile |
| Case database | `~~case-database` | Search legal/policy decisions, get case summaries, analyse reasoning | Meta Oversight Board (osb), court databases |
| Documentation | `~~documentation` | Look up API docs for programming libraries | Context7, DevDocs |
| AI assistant | `~~ai-assistant` | Delegate analysis to another AI model | Gemini (gemini), OpenAI |

## Resolution rules

1. The agent inspects available MCP servers at session start.
2. When a skill references `~~email`, the agent uses whichever email server
   is connected (e.g., `mcp__outlook__*` tools, or `mcp__gmail__*`).
3. If no server matches a category, the agent skips that step or asks the
   user how to proceed.
4. PKB tools are always available and referenced directly (e.g.,
   `mcp__pkb__create_task`).

## Configuring connectors

Connectors are configured through your MCP server setup — the plugin does not
manage them directly. To add or change a connector:

- **Claude Code**: Add the MCP server to your project's `.mcp.json` or global settings.
- **Gemini CLI**: Add the MCP server to your extension's `gemini-extension.json`.
- **Cowork**: Connect the tool through the Cowork desktop app.

The plugin will automatically detect available servers and route operations
to the appropriate connector.
