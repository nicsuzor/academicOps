---
title: "academicOps Infrastructure"
type: infrastructure
description: "Framework infrastructure details including environment variables, directory structure, path conventions, three-tier loading system, and Basic Memory (bmem) integration."
tags:
  - infrastructure
  - environment
  - paths
  - three-tier
  - framework
relations:
  - "[[ARCHITECTURE]]"
  - "[[paths.toml]]"
---

# academicOps Infrastructure

## Environment Variables

- `$ACADEMICOPS`: Framework repository (typically `/home/nic/src/bot`)
- `$ACADEMICOPS_PERSONAL`: User customizations (personal tier)
- `$PWD`: Current project directory

## Directory Structure

```
$ACADEMICOPS/          # Framework repository
├── agents/                # Subagents (slash commands load these)
├── commands/              # Slash command definitions
├── skills/                # Skills (Skill tool loads these)
├── hooks/                 # SessionStart, PostToolUse, Stop hooks
├── core/                  # Universal instructions (SessionStart loads)
├── docs/                  # Framework documentation
│   ├── bots/              # Framework dev context (SessionStart loads)
│   └── INSTRUCTION-INDEX.md  # Complete file registry
├── scripts/               # Supporting automation
└── chunks/                # Shared context modules (symlinked to skills/*/resources/)
```

## Path Conventions

**CRITICAL**: File paths in the academicOps framework:

## Three-Tier Loading System

SessionStart hook auto-loads instructions from three tiers:

1. **Framework**: `$ACADEMICOPS/core/`
2. **Personal**: `$ACADEMICOPS_PERSONAL/core/` (user customizations)
3. **Project**: `$PWD/docs/bots/` (project-specific context)

**NOTE**: Skills do NOT receive SessionStart hooks. Skills access framework context via `@resources/` symlinks only.

## Knowledge Organization (bmem)

**basic-memory** (internal ref: `bmem`) provides vector search and relational mapping:

- **MCP Server**: `mcp__basic-memory__*` tools (read_note, write_note, search_notes, open_entities, create_relation)
- **Project**: `ns` Personal repository ($ACADEMICOPS_PERSONAL)
- **Storage**: Markdown files with YAML frontmatter
- **Access Pattern**: Just-in-time concept loading via vector search
