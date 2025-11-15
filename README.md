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

### For Users

1. Download the latest release from GitHub
2. Extract: `tar -xzf aops-VERSION.tar.gz`
3. Run setup: `bash aops-VERSION/scripts/setup.sh`

See INSTALL.md in the release archive for detailed instructions.

### For Developers

Use `scripts/setup.sh` to symlink configuration to `~/.claude/`. This applies infrastructure globally to all of a user's Claude Code sessions.

## Deployment

### Creating a Release Package

To package the framework for distribution to GitHub releases:

```bash
# Create deployment package (auto-versioned from git tags or date)
python3 scripts/package_deployment.py

# Or specify a custom version
python3 scripts/package_deployment.py --version v1.0.0

# Output will be in dist/aops-VERSION.tar.gz
```

The packaging script:

- Includes all necessary files (skills, hooks, scripts, config, docs)
- Excludes development files (tests, experiments, .git, __pycache__)
- Generates INSTALL.md with installation instructions
- Creates MANIFEST.json with package metadata

### Publishing to GitHub

```bash
# Create a new release with the generated archive
gh release create v1.0.0 dist/aops-v1.0.0.tar.gz \
  --title "aOps v1.0.0" \
  --notes "Release notes here"

# Or upload manually through GitHub web interface
```
