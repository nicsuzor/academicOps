# Project-Specific Setup Guide

This guide explains how to set up project-specific repositories that work seamlessly with academicOps agents.

## Overview

The academicOps agent system is designed to be **generic and project-agnostic**. This means:

- Agent instructions in `bot/agents/` work across multiple projects
- Project-specific configuration happens in each project's repository
- All agent training issues are tracked centrally in academicOps
- Projects maintain their own domain-specific documentation and tooling

## Setting Up a New Project

### 1. Basic Structure

Every project that uses academicOps agents should follow this structure:

```
your-project/
├── CLAUDE.md                    # Points to docs/agents/INSTRUCTIONS.md
├── docs/
│   ├── AGENT_INSTRUCTIONS.md    # Project-specific agent configuration
│   └── agents/                  # Project-specific agent instructions (optional)
│       ├── debugger.md         # Custom debugging instructions
│       └── tester.md           # Custom testing instructions
└── [project-specific files]
```

### 2. Required Files

#### `CLAUDE.md`

```markdown
Read `./docs/agents/INSTRUCTIONS.md` for project instructions.
```

#### `docs/AGENT_INSTRUCTIONS.md`

Template:

```markdown
# Agent Instructions for [Project Name]

This is the project-specific configuration for [Project Name].

## Project Mission

[Brief description of what this project does]

## 🚨 CRITICAL FAILURE MODES - ZERO TOLERANCE 🚨

[Project-specific patterns that must be avoided]

## Key Technical Context

- **Repository**: @[org]/[project]
- **Architecture**: [Brief architecture description]
- **Testing**: [Testing approach and commands]
- **Configuration**: [Config system used]

## Workflow Enforcement

[Project-specific workflow requirements]
```

### 3. Agent Instructions Directory

For complex projects, create `docs/agents/` with project-specific agent instructions:

- **File naming**: Use snake_case (e.g., `debugger.md`, `data_processor.md`)
- **Relative paths only**: All references must be relative to project root
- **Self-contained**: Must work without academicOps structure

### 4. Key Principles

#### Self-Contained Projects

- **No external dependencies**: Projects must work independently of academicOps
- **Relative paths only**: Never use `@projects/` or parent directory references
- **Complete documentation**: All necessary context included in project

#### Generic Agent System

- **Common patterns**: Use academicOps agents for common tasks (debugging, testing, documentation)
- **Project extensions**: Add project-specific agents only when necessary
- **Central tracking**: All agent improvements tracked in academicOps issues

## Migration from Legacy Structure

If migrating from an older structure:

1. **Move deprecated files**: `docs/bots/` → `docs/agents/` (review first)
2. **Update paths**: Change absolute to relative paths
3. **Standardize naming**: Convert to snake_case
4. **Remove confusion**: Eliminate `docs/agent/` (singular) directories

## Critical: Tool Usage Standards

**ALL agents MUST use these commands:**

- ✅ `uv sync` (NOT `pip install` or `uv run pip`)
- ✅ `uv run python` (NOT `python` or `python3`)
- ✅ `uv run pytest` (NOT `pytest`)

These ensure proper virtual environment and dependency management.

## Virtual Environment Strategy

### writing/.venv (Development Environment)

- **Purpose**: Convenience venv for cross-project development
- **Contents**: All tools needed for working across multiple projects
- **Buttermilk**: Installed as editable (`uv pip install -e ./projects/buttermilk`)
- **Usage**: Changes to buttermilk immediately available to dependent projects

### projects/buttermilk/.venv (Distribution Testing)

- **Purpose**: Isolated environment for testing buttermilk as a package
- **Contents**: Only dependencies from buttermilk's pyproject.toml
- **Testing**: Validates buttermilk works as if installed by external users
- **Important**: Do NOT install other writing projects here

### Other Project venvs (Optional)

- Individual projects MAY have their own venvs for isolated testing
- For development, can use writing/.venv instead
- For distribution testing, use isolated venv like buttermilk does

### Workflow

1. **Develop buttermilk changes**: Work in buttermilk/, test in buttermilk/.venv
2. **Use in other projects**: Changes automatically available via editable install in writing/.venv
3. **Package osbchatmcp**: Test against buttermilk/.venv to catch dependency issues

## Working with academicOps Agents

### For Users

- Add `@bot/agents/[agent_name].md` to trigger specific agents
- Create issues in academicOps for agent improvements
- Follow project-specific instructions in `docs/AGENT_INSTRUCTIONS.md`

### For Developers

- Test agent instructions across multiple projects
- Keep generic logic in academicOps `bot/agents/`
- Add project-specific extensions in project `docs/agents/`

## Examples

### Buttermilk Project

- Scientific workflow system
- Heavy use of debugging and testing agents
- Custom `docs/agents/debugger.md` with domain-specific tools

### MediaMarkets Project

- Data analysis pipeline
- Custom data processing agents
- Integration with external APIs

## Support

- **Agent Issues**: Create in academicOps repo with `[project]` prefix
- **Project Issues**: Create in project repo for domain-specific problems
- **Documentation**: Update this guide for new patterns
