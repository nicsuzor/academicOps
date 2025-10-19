# academicOps Agent Framework

A modular, hierarchical agent framework for rigorous, context-aware automation in academic research projects.

## Quick Start

```bash
# Set environment variable
export ACADEMICOPS_BOT=/path/to/academicOps

# Run setup in your project
cd /path/to/your/project
$ACADEMICOPS_BOT/scripts/setup_academicops.sh

# Launch Claude Code
claude
```

## What is academicOps?

**academicOps** provides a structured agent system with:

- **Specialized agents** for different workflows (strategy, development, code review, analysis)
- **Automated validation hooks** that enforce quality standards and best practices
- **Hierarchical instruction loading** (framework → personal → project)
- **Git commit hooks** that prevent documentation bloat
- **Zero-configuration context** loaded at every session start

## Core Principles

1. **Data Boundaries**: `bot/` = PUBLIC (GitHub), everything else = PRIVATE
2. **Project Isolation**: Project-specific content belongs ONLY in the project repository
3. **Fail-Fast Philosophy**: No fallbacks, no defensive programming, no workarounds
4. **Self-Documenting**: No new .md files except research manuscripts—use `--help`, inline comments, and issue templates
5. **Python Execution**: Always use `uv run python` (never bare `python` or `python3`)

**Full rules**: See `agents/_CORE.md`

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

## Available Agents

Invoke specialized agents for different workflows:

- **`@agent-trainer`** - Maintains the agent framework itself (meta-system)
- **`@agent-strategist`** - Planning, task management, project coordination
- **`@agent-developer`** - Code implementation, testing, debugging
- **`@agent-code-review`** - Code review and git commit operations (only agent that can commit)
- **`@agent-analyst`** - Data analysis workflows (dbt, SQL, data pipelines)
- **`@agent-supervisor`** - Orchestrates complex multi-agent workflows
- **`@agent-test-cleaner`** - Ruthlessly simplifies test suites

## Slash Commands

Available project commands:

- **`/ops`** - Load academicOps framework help and commands
- **`/ttd`** - Load test-driven development workflow
- **`/trainer`** - Activate agent trainer mode
- **`/log-failure`** - Log agent performance failures to experiment tracking

## Automated Enforcement

academicOps enforces quality through multiple validation layers:

### Claude Code Hooks (Runtime Validation)

Configured in `.claude/settings.json`, automatically enforced during Claude Code sessions:

- **SessionStart** - Loads hierarchical instructions (`_CORE.md` from bot → personal → project)
- **PreToolUse** - Validates every tool call against agent permissions:
  - Blocks `.md` file creation (except research papers)
  - Requires `uv run` prefix for Python execution
  - Blocks inline Python (`python -c`)
  - Warns non-code-review agents about git commits
  - Prevents `/tmp` test files (violates replication principle)
- **SubagentStop/Stop** - Validates agent completion

### Git Commit Hooks (Pre-Commit Quality)

Installed via `setup_academicops.sh`, enforced before every git commit:

- **Documentation bloat prevention** - Blocks new `.md` files unless:
  - Research papers (`papers/`, `manuscripts/`)
  - Agent instructions (`agents/*.md` - executable code)
  - Explicitly confirmed as allowed content
- **Python code quality** (via `.pre-commit-config.yaml`):
  - `ruff-check` - Linting with auto-fixes
  - `ruff-format` - Code formatting
  - `mypy` - Static type checking
  - `radon` - Complexity metrics
  - `pytest` - Fast unit tests

### Permission System

Fine-grained tool restrictions in `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run pytest:*)",
      "Bash(uv run python:*)"
    ],
    "deny": [
      "Write(**/*.md)",
      "Write(**/*.env*)"
    ]
  }
}
```

## Installation & Setup

See `INSTALL.md` for detailed setup instructions.

## Architecture

See `ARCHITECTURE.md` for complete system design.

## Testing

Use: `uv run pytest`
