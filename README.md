---
title: aOps - LLM Agent Infrastructure
type: documentation
entity_type: note
tags:
- llm-agents
- automation
- infrastructure
permalink: aops/readme
---

# aOps - LLM Agent Infrastructure

Generic utility scripts and LLM agent instructions for Claude Code automation.

This repository is a submodule of `${AO}` (currently `/home/nic/src/writing`) at `${AO}/aOps`.

## Core Principles

**MINIMAL.** We actively fight bloat. Every file must earn its place.

## Structure

```
${AO}/aOps/
├── skills/           # Reusable workflows
├── hooks/            # Claude Code automation hooks
├── scripts/          # Utility scripts
├── config/           # Configuration files
├── core/             # Core instructions (currently empty)
├── docs/             # Documentation
└── resources/        # External references
```

## Key Skills

- **analyst**: Data analysis (dbt, Streamlit, statistical methods)
- **bmem-ops**: Basic Memory operations (CRUD notes)
- **tasks**: Task lifecycle management
- **email**: Email processing (Outlook MCP)
- **git-commit**: Conventional commit workflow
- **context-search**: Semantic search across knowledge base
- **supervisor**: Orchestrates multi-agent workflows
- **tja-research**: TJA project research workflow

## Hooks

Python modules that enforce automation at Claude Code lifecycle events:

- **load_instructions.py**: Load context at session start
- **autocommit_tasks.py**: Auto-commit task changes
- **validate_tool.py**: Validate tool usage
- **validate_stop.py**: Validate session completion
- **stack_instructions.py**: Conditional instruction loading
- **log_*.py**: Event logging

## Installation

Symlink configuration to `~/.claude/`:

```bash
ln -sf ${AO}/aOps/hooks ~/.claude/hooks
ln -sf ${AO}/aOps/skills ~/.claude/skills
ln -sf ${AO}/aOps/config/settings.json ~/.claude/settings.json
```

This applies infrastructure globally to all Claude Code sessions.

## Configuration

- **config/settings.json**: Claude Code settings
- **config/mcp.json**: MCP server configuration
- **paths.toml**: Path configuration for scripts
- **paths.sh**: Generated shell environment variables

## Observations

- This repo is PRIVATE and specific to @nicsuzor's workflow
- Uses `uv` for Python environment management
- All Python commands: `uv run <command>`
- Hydra-based config (no environment variables in configs)
