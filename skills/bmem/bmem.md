---
title: bmem Knowledge Base Skill
type: skill
permalink: bmem-skill-overview
tags:
  - skill
  - knowledge-base
  - bmem
---

# bmem Knowledge Base Skill

## Overview

The bmem skill manages the personal knowledge base stored in `$ACA_DATA/`. It handles three core operations:

1. **Capture** - Extract knowledge from sessions, create notes
2. **Validate** - Check format compliance, fix issues
3. **Prune** - Remove low-value content, extract facts before deletion

## System

- **Backend**: Basic Memory 0.16.1 (MCP-enabled semantic knowledge graph)
- **Format**: Markdown with YAML frontmatter (Obsidian-compatible)
- **Storage**: `data/` hierarchy
- **Access**: MCP tools only (`mcp__bmem__*`)

## Key Principles

### One Thing, Not Two

bmem memories ARE markdown files. The database is an index for search, not separate storage. When you create a note via MCP, you create one markdown file.

### Approved Categories Only

All observations must use approved categories from [[references/approved-categories-relations.md]]. Inventing categories breaks the knowledge graph.

### Write Access via MCP

Never write `data/` files directly. Always use `mcp__bmem__write_note()` or `mcp__bmem__edit_note()`.

## Workflows

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| [[workflows/capture.md]] | Session mining, note creation | Default / "save this" |
| [[workflows/validate.md]] | Format + location compliance | "fix bmem" / "validate" |
| [[workflows/prune.md]] | Value-based cleanup | "clean up" / "declutter" |

## Relations

- part_of [[skills]]
- implements [[Knowledge Management Philosophy]]
