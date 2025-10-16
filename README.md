# academicOps Agent Framework
A modular, hierarchical agent framework for rigorous, context-aware automation in academic research projects.

**Core instructions**: Loaded automatically via `bot/scripts/validate_env.py` at session start.

**Architecture**: See `bot/docs/ARCHITECTURE.md` for complete design.

---


1. **Data Boundaries**: `bot/` = PUBLIC (GitHub), everything else = PRIVATE
2. **Project Isolation**: Project-specific content belongs ONLY in the project repository
3. **Fail-Fast Philosophy**: No fallbacks, no defensive programming, no workarounds
4. **Python Execution**: Always use `uv run python` (never bare `python` or `python3`)
5. **Documentation**: No new .md files except research manuscripts

**Details**: See `bot/agents/_CORE.md` for complete rules.

---

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

## Installation

not yet.

## Testing

Use: `uv run pytest`
