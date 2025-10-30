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
    ├── commands/              # Slash command definitions
    ├── config/                # Global configuration
    ├── docs/                  # Generic documentation (no private data)
    ├── experiments/           # Experiment tracking logs
    ├── hooks/                 # Claude Code hook scripts
    ├── prompts/               # Agent prompt templates
    ├── scripts/               # Automation tools
    ├── skills/                # Packaged skill sources
    └── tests/                 # Test framework
```

## Available Agents

Specialized agents accessed via slash commands or Task tool:

- **`trainer`** (`/trainer`) - Maintains the agent framework itself (meta-system)
- **`strategist`** (`/STRATEGIST`) - Planning, facilitation, silent context capture
- **`developer`** (`/dev`) - Code implementation, TDD workflow, debugging
- **`code-review`** (invoked by other agents) - Code review and git commit operations
- **`supervisor`** (Task tool) - Orchestrates complex multi-step workflows

## Slash Commands

Available project commands:

- **`/analyst`** - Load analyst skill for academic research data analysis (dbt & Streamlit)
- **`/dev`** - Load development workflow and coding standards
- **`/error`** - Quick experiment outcome logging (aOps repo only)
- **`/log-failure`** - Log agent performance failures to experiment tracking
- **`/ops`** - academicOps framework help and commands
- **`/STRATEGIST`** - Strategic thinking partner with silent context capture
- **`/trainer`** - Activate agent trainer mode
- **`/ttd`** - Load test-driven development workflow

## Skills

Portable, reusable workflows available globally (installed in `~/.claude/skills/`):

- **`agent-initialization`** - Create/update AGENT.md skill index files
- **`analyst`** - Academic research data analysis (dbt, Streamlit, academicOps best practices)
- **`aops-bug`** - Track bugs, agent violations, framework improvements in academicOps
- **`aops-trainer`** - Review and improve agents, skills, hooks, configurations
- **`claude-hooks`** - Create, configure, debug Claude Code hooks with technical reference
- **`claude-md-maintenance`** - Maintain CLAUDE.md files with @reference patterns
- **`git-commit`** - Validate code quality and execute commits with conventional format
- **`github-issue`** - Manage GitHub issues with exhaustive search and precise documentation
- **`no-throwaway-code`** - Intervention skill enforcing Axiom 15 (no temporary Python scripts)
- **`skill-creator`** - Guide for creating effective skills
- **`skill-maintenance`** - Ongoing skill maintenance and evolution
- **`strategic-partner`** - Strategic facilitation and thinking partnership
- **`task-management`** - Proactive task/context capture to personal knowledge base
- **`test-writing`** - Test creation enforcing integration test patterns and TDD

Skills are invoked automatically by agents or explicitly via the Skill tool.

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
