# academicOps Agent Framework

A modular, hierarchical agent framework for rigorous, context-aware automation in research projects.

---

## Core Axioms (Inviolable Rules)

These rules are **non-negotiable** and apply to all agents at all times:

1. **Data Boundaries**: `bot/` = PUBLIC (GitHub), everything else = PRIVATE
2. **Project Isolation**: Project-specific content belongs ONLY in the project repository
3. **Project Independence**: Projects (submodules) must work independently without cross-dependencies
4. **Fail-Fast Philosophy**: No fallbacks, no defensive programming, no workarounds, no backwards compatibility
5. **Scope Detection**: Load project context before ANY work

**Details**: See `bot/docs/AGENT-INSTRUCTIONS.md` and `docs/INSTRUCTIONS.md`

## Tool Usage Rules

- **Dependencies**: Managed by `uv`. Only use `uv run ...` to call python commands


## Repository Structure

```
${OUTER}/                      # User's parent repository (PRIVATE)
├── data/                      # Personal task/project database
│   ├── goals/                 # Strategic goals
│   ├── projects/              # Active projects
│   ├── tasks/                 # Task management
│   └── views/                 # Aggregated views
├── docs/                      # System documentation
│   └── projects/              # Cross-project coordination (NOT project content)
├── projects/                  # Academic project submodules (self-contained)
│   └── {project}/
│       └── docs/              # Project-specific content goes HERE
└── bot/                       # THIS SUBMODULE (PUBLIC as nicsuzor/academicOps)
    ├── agents/                # Agent persona definitions
    ├── scripts/               # Automation tools
    ├── docs/                  # Generic documentation (no private data)
    └── tests/                 # Test framework
```

**Path Resolution**: Use environment variables for portability:

- `$ACADEMIC_OPS_DATA` - Data directory
- `$ACADEMIC_OPS_SCRIPTS` - Scripts directory
- `$ACADEMIC_OPS_DOCS` - Documentation directory

---

## Available Agents

- **base**: Default agent for executing predefined workflows
- **trainer**: Improving agent instructions and maintaining documentation
- **developer**: Writing, refactoring, testing, and debugging code
- **analyst**: Data analysis, evaluation, and generating insights
- **strategist**: Planning, facilitation, and project memory management (auto-extraction)
- **academic_writer**: Expanding notes into academic prose with source fidelity
- **documenter**: Creating and maintaining documentation
- **mentor**: Strategic guidance when stuck or facing complex decisions (read-only)

**Details**: See `bot/agents/{agent_name}.md` for full specifications

---

## Quick Reference

**For setup instructions**: See `bot/docs/SETUP.md`

**For detailed instructions**: See `bot/docs/AGENT-INSTRUCTIONS.md`

**For agent-specific behavior**: See `bot/agents/{agent_name}.md`

**For testing**: See `bot/tests/prompts/CONTEXT-AWARENESS-TESTS.md`

**For path configuration**: See `bot/docs/PATH-RESOLUTION.md`

**For auto-extraction patterns**: See `bot/docs/AUTO-EXTRACTION.md`
