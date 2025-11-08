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

This repository is a submodule of `${ACA}` at `${AOPS}`.

## Core Principles

- [[docs/_CORE.md]]
- [[docs/_AXIOMS.md]]

## Structure

```
${ACA}                # User's home repo (PRIVATE)
${AOPS}/              # Automation (PUBLIC)
├── skills/           # Reusable workflows
├── hooks/            # Claude Code automation hooks
├── scripts/          # Utility scripts
├── config/           # Configuration files
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

- Use `setup.sh` to symlink configuration to `~/.claude/`. This applies infrastructure globally to all of a user's Claude Code sessions.
