---
title: Infrastructure Reference
type: reference
entity_type: note
tags:
  - infrastructure
  - paths
  - environment
relations:
  - "[[AXIOMS]]"
  - "[[AGENT-BEHAVIOR]]"
permalink: bots/chunks/infrastructure-2
---

# Infrastructure Reference

## Repository Structure

```
~/src/writing/          # Home repository (PRIVATE)
├── aOps/                   # Bot infrastructure (PUBLIC, git tracked)
│   ├── chunks/             # Shared context modules
│   ├── skills/             # Packaged skills
│   ├── hooks/              # Claude Code hooks
│   ├── scripts/            # Supporting automation
│   ├── config/             # Configuration files
│   └── resources/          # External docs/references
├── data/                   # User data (tasks, projects, goals)
└── projects/               # Project submodules
```

## Path Conventions

All paths are relative to `~/src/writing/` - no environment variables needed.

## Knowledge Organization (Basic Memory)

**basic-memory** (internal ref: `bmem`) provides vector search and relational mapping:

- **MCP Server**: `mcp__bmem__*` tools (read_note, write_note, search_notes, build_context)
- **Project**: `writing` - Personal repository (`~/src/writing/`)
- **Storage**: Markdown files with YAML frontmatter
- **Access Pattern**: Just-in-time concept loading via vector search
