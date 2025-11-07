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
  - "[[chunks/AXIOMS]]"
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

- **Commands**: `$ACADEMICOPS/commands/trainer.md` (NOT `.claude/commands/`)
- **Skills**: `$ACADEMICOPS/skills/skill-name/SKILL.md`
- **Agents**: `$ACADEMICOPS/agents/agent-name.md`
- **Hooks**: `$ACADEMICOPS/hooks/hook_name.py`
- **Core**: `$ACADEMICOPS/core/_CORE.md`

Skills installed system-wide are in `~/.claude/skills/skill-name/SKILL.md`

## Three-Tier Loading System

SessionStart hook auto-loads instructions from three tiers:

1. **Framework**: `$ACADEMICOPS/core/` and `$ACADEMICOPS/docs/bots/`
2. **Personal**: `$ACADEMICOPS_PERSONAL/core/` (user customizations)
3. **Project**: `$PWD/docs/bots/` (project-specific context)

**NOTE**: Skills do NOT receive SessionStart hooks. Skills access framework context via `@resources/` symlinks only.

## Knowledge Organization (bmem)

**basic-memory** (internal ref: `bmem`) provides vector search and relational mapping:

- **MCP Server**: `mcp__basic-memory__*` tools (read_note, write_note, search_notes, open_entities, create_relation)
- **Projects**:
  - `aops`: Framework repository ($ACADEMICOPS)
  - `ns`: Personal repository ($ACADEMICOPS_PERSONAL)
- **Storage**: Markdown files with YAML frontmatter + SQLite graph
- **Access Pattern**: Just-in-time concept loading via vector search

**Directory Conventions**:

```
$ACADEMICOPS_PERSONAL/
├── concepts/              # Concept nodes (core/patterns/workflows)
└── data/tasks_md/         # Task files (inbox/queue/archived)
```

See: Issue #193 for integration architecture and migration status.

## How Projects Use This Framework

- Projects reference via `$ACADEMICOPS` environment variable
- Specialized agents invoked via slash commands (`/trainer`, `/analyst`, `/dev`, etc.)
- Hooks run automatically to validate tool use and load context
- Skills provide reusable, portable workflows across projects
- bmem enables vector search and relational context across repositories
