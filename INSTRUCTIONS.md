---
title: Bot Infrastructure Instructions
type: instructions
entity_type: note
tags:
  - bot-instructions
  - core
  - framework
relations:
  - "[[chunks/AXIOMS]]"
  - "[[chunks/INFRASTRUCTURE]]"
  - "[[chunks/AGENT-BEHAVIOR]]"
permalink: bots/instructions
---

# Bot Infrastructure Instructions

This directory contains bot automation infrastructure for the `~/src/writing/` repository.

## Core Principles

@chunks/AXIOMS.md @chunks/INFRASTRUCTURE.md @chunks/AGENT-BEHAVIOR.md

## Directory Structure

```
bots/
├── chunks/           # Atomic reusable wisdom (AXIOMS, INFRASTRUCTURE, AGENT-BEHAVIOR)
├── skills/           # Reusable workflows (analyst, bmem-ops, tasks, email, etc.)
├── hooks/            # Claude Code automation hooks
├── scripts/          # Task management and setup scripts
├── config/           # Configuration files (mcp.json, paths.toml, settings.json)
└── resources/        # External docs and references
```

## Component Design

### Skills

Reusable workflows loaded via Skill tool. Each skill has:

- **SKILL.md**: Main instructions (<300 lines)
- **resources/**: Symlinks to chunks/ for shared context
- **scripts/**: Optional automation scripts
- **references/**: Optional supporting documentation

**Access chunks via**: `@resources/AXIOMS.md` (symlink to ../../chunks/AXIOMS.md)

### Hooks

Python modules that enforce automation:

- **load_instructions.py**: Load context at session start
- **autocommit_tasks.py**: Auto-commit task changes
- **validate_tool.py**: Validate tool usage
- **validate_stop.py**: Validate session completion
- **stack_instructions.py**: Conditional instruction loading
- **log_*.py**: Event logging

### Scripts

Task management automation:

- **task_add.py**: Create tasks
- **task_process.py**: Modify/archive tasks
- **task_index.py**: Index task database
- **task_view.py**: View task status
- **setup.sh**: Install bots config to ~/.claude/

## Installation

Run `./bots/scripts/setup.sh` to symlink configuration to `~/.claude/`:

- `~/.claude/settings.json` → `bots/config/settings.json`
- `~/.claude/hooks/` → `bots/hooks/`
- `~/.claude/skills/` → `bots/skills/`

This applies bot infrastructure globally to all Claude Code sessions.

## Essential Skills

- **analyst**: Data analysis workflow (dbt, Streamlit, statistical methods)
- **bmem-ops**: Basic Memory operations (create, edit, search notes)
- **tasks**: Task lifecycle management (create, prioritize, complete)
- **email**: Email processing and triage (Outlook MCP)
- **git-commit**: Git commit workflow with conventional commits
- **context-search**: Semantic search across knowledge base
- **tja-research**: TJA project-specific research workflow

## Working Principles

1. **Fail-fast**: No workarounds, no defaults - if tools fail, STOP and report
2. **DRY**: One source of truth - chunks/ contains shared wisdom
3. **Trust git**: No backup files - git is the version control system
4. **Self-documenting**: Code and configuration ARE the documentation
5. **Standard tools**: uv, pytest, pre-commit, ruff, mypy - one golden path
